"""Support functions for sending an SMS."""

from __future__ import annotations

from flask import url_for
import itsdangerous

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
import requests

from baseframe import _

from ... import app
from ...serializers import token_serializer
from ..exc import (
    TransportConnectionError,
    TransportRecipientError,
    TransportTransactionError,
)
from .template import SmsTemplate

__all__ = [
    'make_exotel_token',
    'validate_exotel_token',
    'send_via_exotel',
    'send_via_twilio',
    'send',
]


def make_exotel_token(to: str) -> str:
    """
    Create a signed token for Exotel using the phone number as a verification key.

    Used by :func:`send_via_exotel` to construct a callback URL with a token.
    """
    return token_serializer().dumps({'to': to})


def validate_exotel_token(token: str, to: str) -> bool:
    """Verify the Exotel token created using :func:`make_exotel_token`."""
    try:
        # Allow 7 days validity for the callback token
        payload = token_serializer().loads(token, max_age=86400 * 7)
    except itsdangerous.SignatureExpired:
        # Token has expired
        app.logger.warning("Received expired Exotel token: %s", token)
        return False
    except itsdangerous.BadData:
        # Token is invalid
        app.logger.debug("Received invalid Exotel token: %s", token)
        return False

    phone = payload['to']
    if phone != to:
        app.logger.warning(
            "Received Exotel callback token for a mismatched phone number"
        )
        return False
    return True


def send_via_exotel(phone: str, message: SmsTemplate, callback: bool = True) -> str:
    """
    Send the SMS using Exotel, for Indian phone numbers.

    :param phone: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    sid = app.config['SMS_EXOTEL_SID']
    token = app.config['SMS_EXOTEL_TOKEN']
    payload = {
        'From': app.config['SMS_EXOTEL_FROM'],
        'To': phone,
        'Body': str(message),
        'DltEntityId': message.registered_entityid,
    }
    if message.registered_templateid:
        payload['DltTemplateId'] = message.registered_templateid
    if callback:
        payload['StatusCallback'] = url_for(
            'process_exotel_event',
            _external=True,
            _method='POST',
            secret_token=make_exotel_token(phone),
        )
    try:
        r = requests.post(
            f'https://twilix.exotel.in/v1/Accounts/{sid}/Sms/send.json',
            auth=(sid, token),
            data=payload,
        )
        if r.status_code in (200, 201):
            # All good
            jsonresponse = r.json()
            if isinstance(jsonresponse, (list, tuple)) and jsonresponse:
                transactionid = jsonresponse[0].get('SMSMessage', {}).get('Sid')
            elif isinstance(jsonresponse, dict):
                transactionid = jsonresponse.get('SMSMessage', {}).get('Sid')
            else:
                raise TransportTransactionError(
                    _("Unparseable response from Exotel"), r.text
                )
            return transactionid
        raise TransportTransactionError(_("Exotel API error"), r.status_code, r.text)
    except requests.ConnectionError:
        raise TransportConnectionError(_("Exotel not reachable"))


def send_via_twilio(phone: str, message: SmsTemplate, callback: bool = True) -> str:
    """
    Send the SMS via Twilio, for international phone numbers.

    :param phone: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    # Get SID, Token and From (these are required to make any calls)
    account = app.config['SMS_TWILIO_SID']
    token = app.config['SMS_TWILIO_TOKEN']
    sender = app.config['SMS_TWILIO_FROM']

    # Send (This uses the routing API to deliver SMS via a Low Latency Location).
    # See https://www.twilio.com/docs/global-infrastructure/edge-locations
    client = Client(account, token)

    # Error evaluation is needed as API may fail for a variety of reasons.
    try:
        msg = client.messages.create(
            from_=sender,
            to=phone,
            body=str(message),
            status_callback=url_for(
                'process_twilio_event', _external=True, _method='POST'
            )
            if callback
            else None,
        )
        return msg.sid
    except TwilioRestException as exc:
        # Error codes from
        # https://www.twilio.com/docs/iam/test-credentials#test-sms-messages-parameters-To
        # https://support.twilio.com/hc/en-us/articles/223181868-Troubleshooting-Undelivered-Twilio-SMS-Messages
        # https://www.twilio.com/docs/api/errors#2-anchor
        if exc.code == 21211:
            raise TransportRecipientError(_("This phone number is invalid"))
        if exc.code == 21408:
            app.logger.error("Twilio unsupported country (21408) for %s", phone)
            raise TransportRecipientError(
                _("Hasgeek cannot send messages to phone numbers in this country")
            )
        if exc.code == 21610:
            raise TransportRecipientError(_("This phone number has been blocked"))
        if exc.code == 21612:
            app.logger.error("Twilio unsupported carrier (21612) for %s", phone)
            raise TransportRecipientError(
                _("This phone number is unsupported at this time")
            )
        if exc.code == 21614:
            raise TransportRecipientError(
                _("This phone number cannot receive SMS messages")
            )
        app.logger.error("Unhandled Twilio error %d: %s", exc.code, exc.msg)
        raise TransportTransactionError(
            _("Hasgeek was unable to send a message to this phone number")
        )


senders_by_prefix = [('+91', send_via_exotel), ('+', send_via_twilio)]


def send(phone: str, message: SmsTemplate, callback: bool = True) -> str:
    """
    Send an SMS message to a given phone number and return a transaction id.

    :param phone_number: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    for prefix, sender in senders_by_prefix:
        if phone.startswith(prefix):
            return sender(phone, message, callback)
    raise TransportRecipientError(_("No service provider available for this recipient"))
