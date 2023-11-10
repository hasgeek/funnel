"""Callback handlers from WhatsApp."""

from __future__ import annotations

from flask import current_app, jsonify, request

from baseframe import statsd

from ... import app
from ...models import PhoneNumber, PhoneNumberError, canonical_phone_number, db, sa
from ...typing import ReturnView
from ...utils import abort_null


@app.route('/api/1/whatsapp/meta_event', methods=['GET'])
def process_whatsapp_webhook_verification():
    """Meta requires to verify the webhook URL by sending a GET request with a token."""
    verify_token = app.config['WHATSAPP_WEBHOOK_VERIFY_CODE']
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == verify_token:
            return challenge, 200
        return "Forbidden", 403
    return "Success", 200


@app.route('/api/1/whatsapp/meta_event', methods=['POST'])
def process_whatsapp_event() -> ReturnView:
    """Process WhatsApp callback event."""
    # Register the fact that we got a WhatsApp event.
    # If there are too many rejects, then most likely a hack attempt.
    statsd.incr('phone_number.event', tags={'engine': 'whatsapp', 'stage': 'received'})
    whatsapp_to = abort_null(
        request.json.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses", [{}])[0]
        .get("recipient_id")
    )
    if not whatsapp_to:
        return {'status': 'eror', 'error': 'invalid_phone'}, 422
    # Exotel sends back 0-prefixed phone numbers, not plus-prefixed intl. numbers
    if whatsapp_to.startswith('00'):
        whatsapp_to = '+' + whatsapp_to[2:]
    elif whatsapp_to.startswith('0'):
        whatsapp_to = '+91' + whatsapp_to[1:]
    elif whatsapp_to.startswith('91'):
        whatsapp_to = '+' + whatsapp_to
    try:
        whatsapp_to = canonical_phone_number(whatsapp_to)
    except PhoneNumberError:
        return {'status': 'error', 'error': 'invalid_phone'}, 422

    whatsapp_message = PhoneNumber.query.filter_by(number=whatsapp_to).one_or_none()

    status = (
        request.json.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses", [{}])[0]
        .get("status")
    )

    if status == 'sent':
        whatsapp_message.msg_wa_sent_at = sa.func.utcnow()
    if status == 'delivered':
        whatsapp_message.msg_wa_delivered_at = sa.func.utcnow()
    if status == 'failed':
        whatsapp_message.msg_wa_failed_at = sa.func.utcnow()
    db.session.commit()

    current_app.logger.info(
        "WhatsApp event for phone: %s %s",
        whatsapp_to,
        status,
    )

    statsd.incr(
        'phone_number.event',
        tags={
            'engine': 'whatsapp',
            'stage': 'processed',
            'event': status,
        },
    )
    return jsonify({"status": "ok"}), 200
