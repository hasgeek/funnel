"""Handle email events from service providers (AWS SES)."""

from __future__ import annotations

from email.utils import parseaddr
from typing import List

from flask import current_app, request
import requests

from baseframe import statsd

from ... import app
from ...models import EmailAddress, db
from ...transports.email.aws_ses import (
    SesEvent,
    SesProcessorAbc,
    SnsNotificationType,
    SnsValidator,
    SnsValidatorError,
)
from ...typing import ReturnView


class SesProcessor(SesProcessorAbc):
    """SES message processor."""

    @staticmethod
    def _email_address(address: str) -> EmailAddress:
        """
        Get or add an email address.

        `EmailAddress.add` does an implicit `.get`, but we call `.get` directly because
        `.add` will fail if the address is blocked, while `.get` won't. Why add if we've
        never seen this email address before? Because it may have originated in Hasjob
        or elsewhere in shared infrastructure.

        :param address: Email Address
        :returns: EmailAddress object
        """
        _name, emailaddr = parseaddr(address)
        if not emailaddr:
            raise ValueError(f"Unable to parse email address {address!r}")
        email_address = EmailAddress.get(emailaddr)
        if email_address is None:
            email_address = EmailAddress.add(emailaddr)
        return email_address

    def bounce(self, ses_event: SesEvent) -> None:
        """Record an SES email bounce event."""
        assert ses_event.bounce is not None  # nosec
        for bounced in ses_event.bounce.bounced_recipients:
            email_address = self._email_address(bounced.email)
            if ses_event.bounce.is_hard_bounce:
                email_address.mark_hard_fail()
            else:
                email_address.mark_soft_fail()

        statsd.incr(
            'email_address.event',
            count=len(ses_event.bounce.bounced_recipients),
            tags={'engine': 'aws_ses', 'stage': 'processed', 'event': 'bounced'},
        )

    def delayed(self, ses_event: SesEvent) -> None:
        """Record an SES email delayed event."""
        assert ses_event.delivery_delay is not None  # nosec
        for failed in ses_event.delivery_delay.delayed_recipients:
            email_address = self._email_address(failed.email)
            email_address.mark_soft_fail()

        statsd.incr(
            'email_address.event',
            count=len(ses_event.delivery_delay.delayed_recipients),
            tags={'engine': 'aws_ses', 'stage': 'processed', 'event': 'delayed'},
        )

    def complaint(self, ses_event: SesEvent) -> None:
        """
        Record an SES complaint event.

        As per SES documentation, ISPs may not report the actual email addresses
        that filed the complaint. SES sends us the original recipients who are at
        the same domain, as a _maybe_ list. We respond to complaints by blocking their
        address from further use. Since this is a serious outcome, we can only do this
        when there was a single recipient to the original email.
        https://docs.aws.amazon.com/ses/latest/DeveloperGuide/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-complaint-object
        """
        assert ses_event.complaint is not None  # nosec
        if len(ses_event.complaint.complained_recipients) == 1:
            for complained in ses_event.complaint.complained_recipients:
                if ses_event.complaint.complaint_feedback_type == 'not-spam':
                    email_address = self._email_address(complained.email)
                    email_address.mark_active()
                elif ses_event.complaint.complaint_feedback_type == 'abuse':
                    EmailAddress.mark_blocked(complained.email)
                else:
                    # TODO: Process 'auth-failure', 'fraud', 'other', 'virus'
                    pass
                statsd.incr(
                    'email_address.event',
                    tags={
                        'engine': 'aws_ses',
                        'stage': 'processed',
                        'event': 'complaint',
                        'feedback_type': ses_event.complaint.complaint_feedback_type,
                    },
                )
        else:
            statsd.incr(
                'email_address.event',
                tags={
                    'engine': 'aws_ses',
                    'stage': 'dropped',
                    'event': 'complaint',
                    'feedback_type': ses_event.complaint.complaint_feedback_type,
                },
            )

    def delivered(self, ses_event: SesEvent) -> None:
        """
        Record an SES email delivered event.

        Recipients here are strings and not structures. Unusual, but reflected in
        the documentation.
        https://docs.aws.amazon.com/ses/latest/DeveloperGuide/event-publishing-retrieving-sns-examples.html#event-publishing-retrieving-sns-send
        """
        assert ses_event.delivery is not None  # nosec
        for sent in ses_event.delivery.recipients:
            email_address = self._email_address(sent)
            email_address.mark_sent()
        statsd.incr(
            'email_address.event',
            count=len(ses_event.delivery.recipients),
            tags={'engine': 'aws_ses', 'stage': 'processed', 'event': 'delivered'},
        )

    def opened(self, ses_event: SesEvent) -> None:
        """
        Record an SES email opened event.

        SES doesn't track the recipient that triggered this action, so process this
        only if the original email had a single recipient.
        """
        if len(ses_event.mail.destination) == 1:
            email_address = self._email_address(ses_event.mail.destination[0])
            email_address.mark_active()
            statsd.incr(
                'email_address.event',
                tags={'engine': 'aws_ses', 'stage': 'processed', 'event': 'opened'},
            )
        else:
            statsd.incr(
                'email_address.event',
                tags={'engine': 'aws_ses', 'stage': 'dropped', 'event': 'opened'},
            )

    def click(self, ses_event: SesEvent) -> None:
        """
        Record an SES email click event.

        SES doesn't track the recipient that triggered this action, so process this
        only if the original email had a single recipient.
        """
        if len(ses_event.mail.destination) == 1:
            email_address = self._email_address(ses_event.mail.destination[0])
            email_address.mark_active()
            statsd.incr(
                'email_address.event',
                count=len(ses_event.mail.destination),
                tags={'engine': 'aws_ses', 'stage': 'processed', 'event': 'clicked'},
            )
        else:
            statsd.incr(
                'email_address.event',
                count=len(ses_event.mail.destination),
                tags={'engine': 'aws_ses', 'stage': 'dropped', 'event': 'clicked'},
            )


# Local Variable for Validator, as there is no need to instantiate it every time we get
# a notification (It could be 10 a second at peak)
validator: SnsValidator = SnsValidator()

# SES Message Processor
processor: SesProcessor = SesProcessor()

# SNS Headers that should be present in all messages
sns_headers: List[str] = [
    'x-amz-sns-message-type',
    'x-amz-sns-message-id',
    'x-amz-sns-topic-arn',
]


@app.route('/api/1/email/ses_event', methods=['POST'])
def process_ses_event() -> ReturnView:
    """
    Process SES Events from AWS.

    The events are sent based on the configuration set of the outgoing email.
    """
    # Register the fact that we got an SES event. If there are too many rejections,
    # then it is a hack or DoS attempt.
    statsd.incr('email_address.event', tags={'engine': 'aws_ses', 'stage': 'received'})

    # Check for standard SNS headers and reject event if they are not found
    for header in sns_headers:
        if not request.headers.get(header):
            statsd.incr(
                'email_address.event',
                tags={
                    'engine': 'aws_ses',
                    'stage': 'rejected',
                    'error': 'missing_headers',
                },
            )
            return {'status': 'error', 'error': 'not_json'}, 422

    # Get the JSON message
    message = request.get_json(force=True, silent=True)
    if not message:
        statsd.incr(
            'email_address.event',
            tags={'engine': 'aws_ses', 'stage': 'rejected', 'error': 'bad_json'},
        )
        return {'status': 'error', 'error': 'not_json'}, 422

    # Validate the message
    try:
        validator.topics = app.config['SES_NOTIFICATION_TOPICS']
        validator.check(message)
    except SnsValidatorError:
        current_app.logger.warning("SNS/SES event failed validation: %r", message)
        statsd.incr(
            'email_address.event',
            tags={
                'engine': 'aws_ses',
                'stage': 'rejected',
                'error': 'validation_failure',
            },
        )
        return {
            'status': 'error',
            'error': 'validation_failure',
        }, 422

    # Message Type
    m_type = message.get('Type')

    # Subscription confirmation
    if m_type == SnsNotificationType.SubscriptionConfirmation.value:
        # We must confirm the subscription request
        resp = requests.get(message['SubscribeURL'], timeout=30)
        statsd.incr(
            'email_address.event',
            tags={
                'engine': 'aws_ses',
                'stage': 'processed',
                'event': 'subscription_confirmation',
                'status_code': resp.status_code,
            },
        )
        if resp.status_code != 200:
            return {'status': 'error', 'error': 'subscription_failed'}, 422
        return {'status': 'ok', 'message': 'subscription_success'}

    # Unsubscribe confirmation
    if m_type == SnsNotificationType.UnsubscribeConfirmation.value:
        # We don't want to unsubscribe, so request a resubscribe. Unsubscribe requests
        # are typically in response to server errors. If an actual unsubscribe is
        # required, this code must be disabled, or the server must be taken offline
        resp = requests.get(message['SubscribeURL'], timeout=30)
        statsd.incr(
            'email_address.event',
            tags={
                'engine': 'aws_ses',
                'stage': 'processed',
                'event': 'unsubscribe_confirmation',
                'status_code': resp.status_code,
            },
        )
        if resp.status_code != 200:
            return {'status': 'error', 'error': 'resubscribe_failed'}, 422
        return {'status': 'ok', 'message': 'resubscribe_success'}

    # This is a Notification and we need to process it
    if m_type == SnsNotificationType.Notification.value:
        ses_event: SesEvent = SesEvent.from_json(message.get('Message'))
        processor.process(ses_event)
        db.session.commit()
        return {'status': 'ok', 'message': 'notification_processed'}

    # We'll only get here if there's a misconfiguration
    statsd.incr(
        'email_address.event',
        tags={
            'engine': 'aws_ses',
            'stage': 'dropped',
            'event': m_type,
            'error': 'unknown_message_type',
        },
    )
    return {'status': 'error', 'error': 'unknown_message_type'}, 422
