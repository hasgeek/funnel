"""Callback handlers from SMS providers (Exotel and Twilio)."""

from __future__ import annotations

from flask import current_app, request
from twilio.request_validator import RequestValidator

from baseframe import statsd

from ... import app
from ...models import (
    PhoneNumber,
    PhoneNumberError,
    SmsMessage,
    SmsStatusEnum,
    canonical_phone_number,
    db,
    sa,
)
from ...transports.sms import validate_exotel_token
from ...typing import ReturnView


@app.route('/api/1/sms/twilio_event', methods=['POST'])
def process_twilio_event() -> ReturnView:
    """Process SMS callback event from Twilio."""
    # Register the fact that we got a Twilio SMS event.
    # If there are too many rejects, then most likely a hack attempt.
    statsd.incr('phone_number.event', tags={'engine': 'twilio', 'stage': 'received'})

    # Check if we find twilio headers and if not reject it
    signature = request.headers.get('X-Twilio-Signature')
    if not signature:
        statsd.incr(
            'phone_number.event',
            tags={
                'engine': 'twilio',
                'stage': 'rejected',
                'error': 'missing_signature',
            },
        )
        return {'status': 'error', 'error': 'missing_signature'}, 422

    # Create Request Validator
    validator = RequestValidator(app.config['SMS_TWILIO_TOKEN'])
    if not validator.validate(
        request.url, request.form, request.headers.get('X-Twilio-Signature', '')
    ):
        statsd.incr(
            'phone_number.event',
            tags={
                'engine': 'twilio',
                'stage': 'rejected',
                'error': 'invalid_signature',
            },
        )
        return {'status': 'error', 'error': 'invalid_signature'}, 422

    try:
        phone_number = PhoneNumber.add(request.form['To'])
    except PhoneNumberError:
        phone_number = None
    sms_message = SmsMessage.query.filter_by(
        transactionid=request.form['MessageSid']
    ).one_or_none()

    if sms_message:
        sms_message.status_at = sa.func.utcnow()

    if request.form['MessageStatus'] == 'queued':
        if sms_message:
            sms_message.status = SmsStatusEnum.QUEUED
    elif request.form['MessageStatus'] == 'sent':
        if phone_number:
            phone_number.msg_sms_sent_at = sa.func.utcnow()
        if sms_message:
            sms_message.status = SmsStatusEnum.PENDING
    elif request.form['MessageStatus'] == 'failed':
        if phone_number:
            phone_number.msg_sms_failed_at = sa.func.utcnow()
        if sms_message:
            sms_message.status = SmsStatusEnum.FAILED
    elif request.form['MessageStatus'] == 'delivered':
        if phone_number:
            phone_number.msg_sms_delivered_at = sa.func.utcnow()
            phone_number.mark_has_sms(True)
        if sms_message:
            sms_message.status = SmsStatusEnum.DELIVERED
    else:
        if sms_message:
            sms_message.status = SmsStatusEnum.UNKNOWN
    db.session.commit()

    current_app.logger.info(
        "Twilio event for phone: %s %s",
        request.form['To'],
        request.form['MessageStatus'],
    )

    statsd.incr(
        'phone_number.event',
        tags={
            'engine': 'twilio',
            'stage': 'processed',
            'event': request.form['MessageStatus'],
        },
    )
    return {'status': 'ok', 'message': 'sms_notification_processed'}


@app.route('/api/1/sms/exotel_event/<secret_token>', methods=['POST'])
def process_exotel_event(secret_token: str) -> ReturnView:
    """Process SMS callback event from Exotel."""
    # Register the fact that we got a Exotel SMS event.
    # If there are too many rejects, then most likely a hack attempt.
    statsd.incr('phone_number.event', tags={'engine': 'exotel', 'stage': 'received'})

    exotel_to = request.form.get('To', '')
    if not exotel_to:
        return {'status': 'eror', 'error': 'invalid_phone'}, 422
    # Exotel sends back 0-prefixed phone numbers, not plus-prefixed intl. numbers
    if exotel_to.startswith('00'):
        exotel_to = '+' + exotel_to[2:]
    elif exotel_to.startswith('0'):
        exotel_to = '+91' + exotel_to[1:]
    try:
        exotel_to = canonical_phone_number(exotel_to)
    except PhoneNumberError:
        return {'status': 'error', 'error': 'invalid_phone'}, 422

    # Verify the token based on the canonical number.
    if not validate_exotel_token(secret_token, exotel_to):
        statsd.incr(
            'phone_number.event',
            tags={
                'engine': 'exotel',
                'stage': 'rejected',
                'error': 'invalid_signature',
            },
        )
        return {'status': 'error', 'error': 'invalid_signature'}, 422

    # There are only 3 parameters in the callback as per the documentation
    # https://developer.exotel.com/api/#send-sms
    # SmsSid - The Sid (unique id) of the SMS that you got in response to your request
    # To - Mobile number to which SMS was sent
    # Status - one of: queued, sending, submitted, sent, failed_dnd, failed
    try:
        phone_number = PhoneNumber.add(exotel_to)
    except PhoneNumberError:
        phone_number = None
    sms_message = SmsMessage.query.filter_by(
        transactionid=request.form['SmsSid']
    ).one_or_none()

    if sms_message:
        sms_message.status_at = sa.func.utcnow()

    if request.form['Status'] == 'queued':
        if sms_message:
            sms_message.status = SmsStatusEnum.QUEUED
    elif request.form['Status'] in ('sending', 'submitted'):
        if phone_number:
            phone_number.msg_sms_sent_at = sa.func.utcnow()
        if sms_message:
            sms_message.status = SmsStatusEnum.PENDING
    elif request.form['Status'] in ('failed', 'failed_dnd'):
        if phone_number:
            phone_number.msg_sms_failed_at = sa.func.utcnow()
        if sms_message:
            sms_message.status = SmsStatusEnum.FAILED
    elif request.form['Status'] == 'sent':
        if phone_number:
            phone_number.msg_sms_delivered_at = sa.func.utcnow()
            phone_number.mark_has_sms(True)
        if sms_message:
            sms_message.status = SmsStatusEnum.DELIVERED
    else:
        if sms_message:
            sms_message.status = SmsStatusEnum.UNKNOWN
    db.session.commit()

    current_app.logger.info(
        "Exotel event for phone: %s %s",
        exotel_to,
        request.form['Status'],
    )

    statsd.incr(
        'phone_number.event',
        tags={
            'engine': 'exotel',
            'stage': 'processed',
            'event': request.form['Status'],
        },
    )
    return {'status': 'ok', 'message': 'sms_notification_processed'}
