import json

from flask import jsonify, make_response, request

import requests

from .. import app
from ..aws_ses import (
    Bounce,
    Complaint,
    Delivery,
    DeliveryDelay,
    Processor,
    SesEvent,
    Type,
    Validator,
    ValidatorException,
)
from ..models import EmailAddress


class SesProcessor(Processor):
    """
    SES Message Processor
    """

    def bounce(self, bounce: Bounce) -> None:
        for bounced in bounce.bounced_recipients:
            email = EmailAddress.add(bounced.email_address)
            if bounce.is_hard_bounce():
                email.mark_hard_fail()
            else:
                email.mark_soft_fail()

    def delayed(self, delayed: DeliveryDelay) -> None:
        for failed in delayed.delayed_recipients:
            email = EmailAddress.add(failed.email_address)
            email.mark_soft_fail()

    def complaint(self, complaint: Complaint) -> None:
        for complained in complaint.complained_recipients:
            if complaint.complaint_feedback_type == "not-spam":
                email = EmailAddress.add(complained.email_address)
                email.mark_active()
            else:
                EmailAddress.mark_blocked(complained.email_address)

    def delivered(self, delivery: Delivery) -> None:
        for sent in delivery.recipients:
            EmailAddress.add(sent).mark_sent()


# Local Variable for Validator, as there is no need to instantiate it every time, we get a
# notification (It could be 10 a second at peak)
validator: Validator = Validator()

# SES Message Processor
processor = SesProcessor()


@app.route('/api/1/email/ses_event', methods=['POST'])
def process_ses_event():
    """
    Processes SES Events from AWS. The events are sent based on the configuration set of the outgoing
    email.
    """
    # Try to decode the JSON
    try:
        message = json.loads(request.data)
    except json.decoder.JSONDecodeError:
        error_msg = 'Request body is not in json format.'
        return make_response(jsonify(message=error_msg, status='error'), 400)

    # Validate message
    try:
        validator.topics = app.config['SES_NOTIFICATION_TOPICS']
        validator.check(message)
    except ValidatorException as ex:
        return make_response(jsonify(message=ex.args, status='error'), 400)

    # Message Type
    m_type = message.get('Type')

    # Subscription confirmation
    if m_type == Type.SubscriptionConfirmation.value:
        resp = requests.get(message.get('SubscribeURL'))
        if resp.status_code != 200:
            return make_response(
                jsonify(message='Subscription failed', status='error'), 500
            )
        return make_response(
            jsonify(message='Subscription success', status='Success'), 200
        )

    # unsubscribe confirmation.
    if m_type == Type.UnsubscribeConfirmation.value:
        resp = requests.get(message.get('UnsubscribeURL'))
        if resp.status_code != 200:
            return make_response(
                jsonify(message='un-subscribe failed', status='error'), 500
            )
        return make_response(
            jsonify(message='un-subscribe failed', status='Success'), 200
        )

    # This is a Notification and we need to process it.
    if m_type == Type.Notification.value:
        ses_event: SesEvent = SesEvent.from_json(message.get('Message'))
        processor.process(ses_event)
        return make_response(
            jsonify(message='Notification processed', status='Success'), 200
        )
