"""Callback handlers from WhatsApp."""

from __future__ import annotations

from flask import abort, current_app, request

from baseframe import statsd

from ... import app
from ...models import PhoneNumber, PhoneNumberInvalidError, db, sa
from ...typing import ReturnView
from ...utils import abort_null


@app.route('/api/1/whatsapp/meta_event', methods=['GET'])
def process_whatsapp_webhook_verification():
    """Meta requires to verify the webhook URL by sending a GET request with a token."""
    verify_token = app.config['WHATSAPP_WEBHOOK_SECRET']
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == verify_token:
            return challenge, 200
        return 'Forbidden', 403
    return 'Success', 200


@app.route('/api/1/whatsapp/meta_event', methods=['POST'])
def process_whatsapp_event() -> ReturnView:
    """Process WhatsApp callback event from Meta Cloud API."""
    # Register the fact that we got a WhatsApp event.
    # If there are too many rejects, then most likely a hack attempt.
    statsd.incr(
        'phone_number.event', tags={'engine': 'whatsapp-meta', 'stage': 'received'}
    )
    if not request.json:
        abort(400)

    # FIXME: Handle multiple events in a single call, as it clearly implied by `changes`
    # and `statuses` being a list in this call
    statuses = request.json['entry'][0]['changes'][0]['value']['statuses'][0]
    whatsapp_to = abort_null(statuses['recepient_id'])
    if not whatsapp_to:
        return {'status': 'eror', 'error': 'invalid_phone'}, 422

    try:
        phone_number = PhoneNumber.add(phone=f'+{whatsapp_to}')
    except PhoneNumberInvalidError:
        current_app.logger.info(
            "WhatsApp Meta Cloud API event for phone: %s invalid number for Whatsapp",
            whatsapp_to,
        )
        return {'status': 'error', 'error': 'invalid_phone'}, 422

    msg_status = statuses['status']

    if msg_status == 'sent':
        phone_number.msg_wa_sent_at = sa.func.utcnow()
    elif msg_status == 'delivered':
        phone_number.msg_wa_delivered_at = sa.func.utcnow()
        phone_number.mark_has_wa(True)
    elif msg_status == 'failed':
        phone_number.msg_wa_failed_at = sa.func.utcnow()
    db.session.commit()

    current_app.logger.info(
        "WhatsApp Meta Cloud API event for phone: %s %s",
        whatsapp_to,
        msg_status,
    )

    statsd.incr(
        'phone_number.event',
        tags={
            'engine': 'whatsapp-meta',
            'stage': 'processed',
            'event': msg_status,
        },
    )
    return {'status': 'ok'}, 200
