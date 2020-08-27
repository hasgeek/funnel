from flask import request

import requests

from coaster.views import render_with

from .. import app
from ..models import EmailAddress, db
from ..transports.email.aws_ses import (
    Bounce,
    Complaint,
    Delivery,
    DeliveryDelay,
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

    def bounce(self, bounce: Bounce) -> None:
        for bounced in bounce.bounced_recipients:
            email_address = EmailAddress.get(bounced.email)
            if not email_address:
                email_address = EmailAddress.add(bounced.email)
            if bounce.is_hard_bounce:
                email_address.mark_hard_fail()
            else:
                email_address.mark_soft_fail()

    def delayed(self, delayed: DeliveryDelay) -> None:
        for failed in delayed.delayed_recipients:
            email_address = EmailAddress.get(failed.email)
            if not email_address:
                email_address = EmailAddress.add(failed.email)
            email_address.mark_soft_fail()

    def complaint(self, complaint: Complaint) -> None:
        for complained in complaint.complained_recipients:
            if complaint.complaint_feedback_type == 'not-spam':
                email_address = EmailAddress.get(complained.email)
                if not email_address:
                    email_address = EmailAddress.add(complained.email)
                email_address.mark_active()
            else:
                EmailAddress.mark_blocked(complained.email)

    def delivered(self, delivery: Delivery) -> None:
        # Recipients here are strings and not structures. Unusual, but reflected in
        # the documentation.
        # https://docs.aws.amazon.com/ses/latest/DeveloperGuide/event-publishing-retrieving-sns-examples.html#event-publishing-retrieving-sns-send
        for sent in delivery.recipients:
            email_address = EmailAddress.get(sent)
            if not email_address:
                email_address = EmailAddress.add(sent)
            email_address.mark_sent()


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
