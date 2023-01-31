"""Support functions for sending an Whatsapp messages."""

from __future__ import annotations

from typing import Union

from models import PhoneNumber, PhoneNumberBlockedError
import phonenumbers
import requests

from baseframe import _

from .. import app
from .exc import (
    TransportConnectionError,
    TransportRecipientError,
    TransportTransactionError,
)

__all__ = ['send_wa_via_meta', 'send_wa_via_on_premise']


def get_phone_number(
    phone: Union[str, phonenumbers.PhoneNumber, PhoneNumber]
) -> PhoneNumber:
    if isinstance(phone, PhoneNumber):
        if not phone.number:
            raise TransportRecipientError(_("This phone number is not available"))
        return phone
    try:
        phone_number = PhoneNumber.add(phone)
    except PhoneNumberBlockedError as exc:
        raise TransportRecipientError(_("This phone number has been blocked")) from exc
    if not phone_number.allow_whatsapp:
        raise TransportRecipientError(_("Whatsapp is disabled for this phone number"))
    if not phone_number.number:
        # This should never happen as :meth:`PhoneNumber.add` will restore the number
        raise TransportRecipientError(_("This phone number is not available"))
    return phone_number


def send_wa_via_meta(phone: str, message, callback: bool = True) -> str:
    """
    Send the Whatsapp message using Meta Cloud API.

    :param phone: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    phone_number = get_phone_number(phone)
    sid = app.config['WHATSAPP_PHONE_ID']
    token = app.config['WHATSAPP_TOKEN']
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        'to': phone_number.number,
        "type": "template",
        'body': str(message),
        'DltEntityId': message.registered_entityid,
    }
    try:
        r = requests.post(
            f'https://graph.facebook.com/v15.0/{sid}/messages',
            timeout=30,
            auth=(token),
            data=payload,
        )
        if r.status_code == 200:
            jsonresponse = r.json()
            transactionid = jsonresponse['messages'].get('id')
            return transactionid
        raise TransportTransactionError(_("Whatsapp API error"), r.status_code, r.text)
    except requests.ConnectionError as exc:
        raise TransportConnectionError(_("Whatsapp not reachable")) from exc


def send_wa_via_on_premise(phone: str, message, callback: bool = True) -> str:
    """
    Send the Whatsapp message using Meta Cloud API.

    :param phone: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    phone_number = get_phone_number(phone)
    sid = app.config['WHATSAPP_PHONE_ID']
    token = app.config['WHATSAPP_TOKEN']
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        'to': phone_number.number,
        "type": "template",
        'body': str(message),
        'DltEntityId': message.registered_entityid,
    }
    try:
        r = requests.post(
            f'https://graph.facebook.com/v15.0/{sid}/messages',
            timeout=30,
            auth=(token),
            data=payload,
        )
        if r.status_code == 200:
            jsonresponse = r.json()
            transactionid = jsonresponse['messages'].get('id')
            return transactionid
        raise TransportTransactionError(_("Whatsapp API error"), r.status_code, r.text)
    except requests.ConnectionError as exc:
        raise TransportConnectionError(_("Whatsapp not reachable")) from exc
