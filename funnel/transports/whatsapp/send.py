"""Support functions for sending an WhatsApp messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Union, cast

import phonenumbers
import requests

from baseframe import _

from ... import app
from ...models import PhoneNumber, PhoneNumberBlockedError, sa
from ..exc import (
    TransportConnectionError,
    TransportRecipientError,
    TransportTransactionError,
)


@dataclass
class WhatsappSender:
    """A WhatsApp sender."""

    requires_config: set
    func: Callable
    init: Optional[Callable] = None


def get_phone_number(
    phone: Union[str, phonenumbers.PhoneNumber, PhoneNumber]
) -> PhoneNumber:
    if isinstance(phone, PhoneNumber):
        if not phone.number:
            raise TransportRecipientError(_("This phone number is not available"))
        # TODO: Confirm this phone number is available on WhatsApp
        return phone
    try:
        phone_number = PhoneNumber.add(phone)
    except PhoneNumberBlockedError as exc:
        raise TransportRecipientError(_("This phone number has been blocked")) from exc
    # TODO: Confirm this phone number is available on WhatsApp (replacing `allow_wa`)
    if not phone_number.allow_wa:
        raise TransportRecipientError(_("WhatsApp is disabled for this phone number"))
    if not phone_number.number:
        # This should never happen as :meth:`PhoneNumber.add` will restore the number
        raise TransportRecipientError(_("This phone number is not available"))
    return phone_number


def send_via_meta(phone: str, message, callback: bool = True) -> str:
    """
    Send the WhatsApp message using Meta Cloud API.

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
            phone_number.msg_wa_sent_at = sa.func.utcnow()
            return transactionid
        raise TransportTransactionError(_("WhatsApp API error"), r.status_code, r.text)
    except requests.ConnectionError as exc:
        raise TransportConnectionError(_("WhatsApp not reachable")) from exc


def send_via_hosted(phone: str, message, callback: bool = True) -> str:
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
            phone_number.msg_wa_sent_at = sa.func.utcnow()

            return transactionid
        raise TransportTransactionError(_("WhatsApp API error"), r.status_code, r.text)
    except requests.ConnectionError as exc:
        raise TransportConnectionError(_("WhatsApp not reachable")) from exc


#: Supported senders (ordered by priority)
sender_registry = [
    WhatsappSender(
        {'WHATSAPP_PHONE_ID_HOSTED', 'WHATSAPP_TOKEN_HOSTED'}, send_via_hosted
    ),
    WhatsappSender({'WHATSAPP_PHONE_ID_META', 'WHATSAPP_TOKEN_META'}, send_via_meta),
]

senders = []


def init() -> bool:
    """Process available senders."""
    for provider in sender_registry:
        if all(app.config.get(var) for var in provider.requires_config):
            senders.append(provider.func)
            if provider.init:
                provider.init()
    return bool(senders)


def send(
    phone: Union[str, phonenumbers.PhoneNumber, PhoneNumber],
    message,
    callback: bool = True,
) -> str:
    """
    Send a WhatsApp message to a given phone number and return a transaction id.

    :param phone_number: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    phone_number = get_phone_number(phone)
    phone = cast(str, phone_number.number)
    for sender in senders:
        return sender()
    raise TransportRecipientError(_("No service provider available for this recipient"))
