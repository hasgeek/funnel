from flask import request

from twilio.request_validator import RequestValidator

from baseframe import statsd
from coaster.views import render_with

from .. import app
from ..models import SMS_STATUS, SMSMessage, db


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

    # Create Request Validator
    validator = RequestValidator(app.config['SMS_TWILIO_TOKEN'])
    if not validator.validate(
        request.url, request.form, request.headers.get('X-Twilio-Signature', '')
    ):
        statsd.incr('phone_number.sms.twilio_event.rejected')
        return {'status': 'error', 'error': 'invalid_signature'}, 422

    # FIXME: This code segment needs to change and re-written once Phone Number model is
    # in place.
    # noinspection PyArgumentList

    sms_message = SMSMessage.query.filter_by(
        transactionid=request.form['MessageSid']
    ).one_or_none()
    if sms_message is None:
        sms_message = SMSMessage(
            phone_number=request.form['To'],
            transactionid=request.form['MessageSid'],
            message=request.form['Body'],
        )
        db.session.add(sms_message)

    sms_message.status_at = db.func.utcnow()

    if request.form['MessageStatus'] == 'queued':
        sms_message.status = SMS_STATUS.QUEUED
    elif request.form['MessageStatus'] == 'failed':
        sms_message.status = SMS_STATUS.FAILED
    elif request.form['MessageStatus'] == 'delivered':
        sms_message.status = SMS_STATUS.DELIVERED
    elif request.form['MessageStatus'] == 'sent':
        sms_message.status = SMS_STATUS.PENDING
    else:
        sms_message.status = SMS_STATUS.UNKNOWN
    # Done
    db.session.commit()
    app.logger.info(
        "Twilio event for phone: %s %s",
        request.form['To'],
        request.form['MessageStatus'],
    )
    return {'status': 'ok', 'message': 'sms_notification_processed'}


# FIXME: Dummy function. Will be fixed in subsequent checkins.
@app.route('/api/1/sms/exotel_event/<secret_token>', methods=['POST'])
@render_with(template=None, json=True)
def process_exotel_event(secret_token):
    """Process SMS callback event from Exotel."""
    return {'status': 'ok', 'message': 'sms_notification_processed'}
