from flask import request

import requests

from coaster.views import render_with

from .. import app
from ..models import EmailAddress, db
from ..transports.email.aws_ses import (
    SesEvent,
    SesProcessorAbc,
    SnsNotificationType,
    SnsValidator,
    SnsValidatorException,
)


class SesProcessor(SesProcessorAbc):
    """SES message processor."""

    # `EmailAddress.add` does an implicit `.get`, but we call `.get` first because
    # `.add` will fail if the address is blocked, while `.get` won't. Why add if we've
    # never seen this email address before? Because it may have originated in Hasjob
    # or elsewhere in shared infrastructure.

    def bounce(self, ses_event: SesEvent) -> None:
        for bounced in ses_event.bounce.bounced_recipients:
            email_address = EmailAddress.get(bounced.email)
            if not email_address:
                email_address = EmailAddress.add(bounced.email)
            if ses_event.bounce.is_hard_bounce:
                email_address.mark_hard_fail()
            else:
                email_address.mark_soft_fail()

    def delayed(self, ses_event: SesEvent) -> None:
        for failed in ses_event.delivery_delay.delayed_recipients:
            email_address = EmailAddress.get(failed.email)
            if not email_address:
                email_address = EmailAddress.add(failed.email)
            email_address.mark_soft_fail()

    def complaint(self, ses_event: SesEvent) -> None:
        # As per SES documentation, ISPs may not report the actual email addresses
        # that filed the complaint. SES sends us the original recipients who are at
        # the same domain, as a _maybe_ list. We respond to complaints by blocking their
        # address from further use. Since this is a serious outcome, we can only do this
        # when there was a single recipient to the original email.
        # https://docs.aws.amazon.com/ses/latest/DeveloperGuide/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-complaint-object
        if len(ses_event.complaint.complained_recipients) == 1:
            for complained in ses_event.complaint.complained_recipients:
                if ses_event.complaint.complaint_feedback_type == 'not-spam':
                    email_address = EmailAddress.get(complained.email)
                    if not email_address:
                        email_address = EmailAddress.add(complained.email)
                    email_address.mark_active()
                elif ses_event.complaint.complaint_feedback_type == 'abuse':
                    EmailAddress.mark_blocked(complained.email)
                else:
                    # TODO: Process 'auth-failure', 'fraud', 'other', 'virus'
                    pass

    def delivered(self, ses_event: SesEvent) -> None:
        # Recipients here are strings and not structures. Unusual, but reflected in
        # the documentation.
        # https://docs.aws.amazon.com/ses/latest/DeveloperGuide/event-publishing-retrieving-sns-examples.html#event-publishing-retrieving-sns-send
        for sent in ses_event.delivery.recipients:
            email_address = EmailAddress.get(sent)
            if not email_address:
                email_address = EmailAddress.add(sent)
            email_address.mark_sent()

    def opened(self, ses_event: SesEvent) -> None:
        for email in ses_event.mail.destination:
            email_address = EmailAddress.get(email)
            if not email_address:
                email_address = EmailAddress.add(email)
            email_address.mark_active()

    def click(self, ses_event: SesEvent) -> None:
        for email in ses_event.mail.destination:
            email_address = EmailAddress.get(email)
            if not email_address:
                email_address = EmailAddress.add(email)
            email_address.mark_active()


# Local Variable for Validator, as there is no need to instantiate it every time we get
# a notification (It could be 10 a second at peak)
validator: SnsValidator = SnsValidator()

# SES Message Processor
processor: SesProcessor = SesProcessor()


@app.route('/api/1/email/ses_event', methods=['POST'])
@render_with(json=True)
def process_ses_event():
    """
    Processes SES Events from AWS.

    The events are sent based on the configuration set of the outgoing email.
    """
    # Get the JSON message
    message = request.get_json(silent=True)
    if not message:
        return {'status': 'error', 'error': 'not_json'}, 400

    # Validate the message
    try:
        validator.topics = app.config['SES_NOTIFICATION_TOPICS']
        validator.check(message)
    except SnsValidatorException as exc:
        return {'status': 'error', 'error': 'invalid_topic', 'message': exc.args}, 400

    # Message Type
    m_type = message.get('Type')

    # Subscription confirmation
    if m_type == SnsNotificationType.SubscriptionConfirmation.value:
        resp = requests.get(message.get('SubscribeURL'))
        if resp.status_code != 200:
            return {'status': 'error', 'error': 'subscription_failed'}, 400
        return {'status': 'ok', 'message': 'subscription_success'}

    # Unsubscribe confirmation
    if m_type == SnsNotificationType.UnsubscribeConfirmation.value:
        resp = requests.get(message.get('UnsubscribeURL'))
        if resp.status_code != 200:
            return {'status': 'error', 'error': 'unsubscribe_failed'}, 400
        return {'status': 'ok', 'message': 'unsubscribe_success'}

    # This is a Notification and we need to process it
    if m_type == SnsNotificationType.Notification.value:
        ses_event: SesEvent = SesEvent.from_json(message.get('Message'))
        processor.process(ses_event)
        db.session.commit()
        return {'status': 'ok', 'message': 'notification_processed'}

    # The Path that should never be taken
    return {'status': 'error', 'error': 'unknown_message_type'}, 400
