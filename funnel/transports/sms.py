"""Support functions for sending a short text message."""

import requests

from .. import app
from .base import (
    TransportConnectionError,
    TransportRecipientError,
    TransportTransactionError,
)

__all__ = ['send']


def send_via_exotel(phone_number, message):
    sid = app.config['SMS_EXOTEL_SID']
    token = app.config['SMS_EXOTEL_TOKEN']
    try:
        r = requests.post(
            'https://twilix.exotel.in/v1/Accounts/{sid}/Sms/send.json'.format(sid=sid),
            auth=(sid, token),
            data={
                'From': app.config['SMS_EXOTEL_FROM'],
                'To': phone_number,
                'Body': message,
            },
        )
        if r.status_code in (200, 201):
            # All good
            jsonresponse = r.json()
            if isinstance(jsonresponse, (list, tuple)) and jsonresponse:
                transactionid = jsonresponse[0].get('SMSMessage', {}).get('Sid')
            else:
                transactionid = jsonresponse.get('SMSMessage', {}).get('Sid')
            return transactionid
        raise TransportTransactionError("Exotel API error", r.status_code, r.text)
    except requests.ConnectionError:
        raise TransportConnectionError("Exotel not reachable")


def send_via_twilio(phone_number, message):
    sid = app.config['SMS_TWILIO_SID']
    token = app.config['SMS_TWILIO_TOKEN']
    try:
        r = requests.post(
            'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'.format(
                sid=sid
            ),
            auth=(sid, token),
            data={
                'From': app.config['SMS_TWILIO_FROM'],
                'To': phone_number,
                'Body': message,
            },
        )
        if r.status_code in (200, 201):
            # All good
            jsonresponse = r.json()
            return jsonresponse.get('sid')
        raise TransportTransactionError("Twilio API error", r.status_code, r.text)
    except requests.ConnectionError:
        raise TransportConnectionError("Twilio not reachable")


senders_by_prefix = [('+91', send_via_exotel), ('+', send_via_twilio)]


def send(phone_number, message):
    """Send a message to a phone number and return the transaction id."""
    for prefix, sender in senders_by_prefix:
        if phone_number.startswith(prefix):
            return sender(phone_number, message)
    raise TransportRecipientError("No service provider available for this recipient")
