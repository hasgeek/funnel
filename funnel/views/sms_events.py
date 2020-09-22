from flask import request

from twilio.request_validator import RequestValidator

from baseframe import statsd
from coaster.views import render_with

from .. import app
from ..models import SMS_STATUS, SMSMessage, db
from ..transports.sms import TwilioSmsResponse


@app.route('/api/1/sms/twilio_event', methods=['POST'])
@render_with(template=None, json=True)
def process_twilio_event():
    """Process SMS callback event from Twilio."""

    # Register the fact that we got a Twilio SMS event.
    # If there are too many rejects, then most likely a hack attempt.
    statsd.incr('phone_number.sms.twilio_event.received')

    # Check if we find twilio headers and if not reject it
    signature = request.headers.get('X-Twilio-Signature')
    if not signature:
        statsd.incr('phone_number.sms.twilio_event.rejected')
        return {'status': 'error', 'error': 'missing_signature'}, 422

    # Get the JSON message
    payload = request.get_json(force=True)
    if not payload:
        statsd.incr('phone_number.sms.twilio_event.rejected')
        return {'status': 'error', 'error': 'not_json'}, 422

    # Create Request Validator
    validator = RequestValidator(app.config['SMS_TWILIO_TOKEN'])

    sms_response: TwilioSmsResponse = TwilioSmsResponse.from_dict(payload)
    if not validator.validate(request.base_url, payload, signature):
        app.logger.info("Twilio event: %r", payload)
        statsd.incr('phone_number.sms.twilio_event.rejected')
        return {'status': 'error', 'error': 'invalid_signature'}, 422

    # FIXME: This code segment needs to change and re-written once Phone Number model is in place.
    # noinspection PyArgumentList
    sms_db_model: SMSMessage = SMSMessage(phone_number=sms_response.sender)
    sms_db_model.transactionid = sms_response.sms_sid
    if sms_response.msg_status == 'queued':
        sms_db_model.status = SMS_STATUS.QUEUED
    elif sms_response.msg_status == 'failed':
        sms_db_model.status = SMS_STATUS.FAILED
    elif sms_response.msg_status == 'delivered':
        sms_db_model.status = SMS_STATUS.DELIVERED
    elif sms_response.msg_status == 'sent':
        sms_db_model.status = SMS_STATUS.PENDING
    else:
        sms_db_model.status = SMS_STATUS.UNKNOWN

    # Done
    db.session.commit()
    app.logger.info("Twilio event for phone: %s processed", sms_response.sender)
    return {'status': 'ok', 'message': 'sms_notification_processed'}


# FIXME: Dummy function. Will be fixed in subsequent checkins.
@app.route('/api/1/sms/exotel_event/<secret_token>', methods=['POST'])
@render_with(template=None, json=True)
def process_exotel_event(secret_token):
    """Process SMS callback event from Exotel."""
    return {'status': 'ok', 'message': 'sms_notification_processed'}
