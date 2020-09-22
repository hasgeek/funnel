"""Support functions for sending a short text message."""

from dataclasses import dataclass, field
from typing import Optional

from flask import url_for

from dataclasses_json import config, dataclass_json
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
import requests

from baseframe import _

from .. import app
from .base import (
    TransportConnectionError,
    TransportRecipientError,
    TransportTransactionError,
)

__all__ = ['TwilioSmsResponse', 'send_via_exotel', 'send_via_twilio', 'send']


@dataclass_json
@dataclass
class TwilioSmsResponse:
    """
    SMS status message sent by Twilio during a callback.

    Described at: https://www.twilio.com/docs/sms/send-messages

    * sms_sid: Response ID of the SMS.
    * status:  These could be any of queued, failed, sent, delivered, undelivered
    * msg_status: Same values as status
    * to: Destination Phone number
    * msg_sid: Same values as sms_sid
    * account_sid: Sending Account ID
    * sender: Sending Phone number
    * api_version: API Version
    """

    sms_sid: str = field(metadata=config(field_name='SmsSid'))
    status: str = field(metadata=config(field_name='SmsStatus'))
    msg_status: Optional[str] = field(metadata=config(field_name='MessageStatus'))
    to: str = field(metadata=config(field_name='To'))
    msg_sid: Optional[str] = field(metadata=config(field_name='MessageSid'))
    account_sid: str = field(metadata=config(field_name='AccountSid'))
    sender: str = field(metadata=config(field_name='From'))
    api_version: Optional[str] = field(metadata=config(field_name='ApiVersion'))


def send_via_exotel(phone: str, message: str, callback: bool = True) -> str:
    """
    Send the SMS using Exotel, for Indian phone numbers.

    :param phone: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    sid = app.config['SMS_EXOTEL_SID']
    token = app.config['SMS_EXOTEL_TOKEN']
    try:
        r = requests.post(
            'https://twilix.exotel.in/v1/Accounts/{sid}/Sms/send.json'.format(sid=sid),
            auth=(sid, token),
            data={
                'From': app.config['SMS_EXOTEL_FROM'],
                'To': phone,
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


def send_via_twilio(phone: str, message: str, callback: bool = True) -> str:
    """
    Send the SMS via Twilio, for international phone numbers.

    :param phone: Phone Number
    :param message: Message to deliver to Phone number
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
            body=message,
            status_callback=url_for(
                'process_twilio_event', _external=True, _method='POST'
            )
            if callback
            else None,
        )
        return msg.sid
    except TwilioRestException as e:
        # Error codes from
        # https://www.twilio.com/docs/iam/test-credentials#test-sms-messages-parameters-To
        if e.code == 21211:
            raise TransportRecipientError(_("This phone number is invalid"))
        if e.code in (21612, 21408):
            raise TransportRecipientError(
                _("This phone number is unsupported at this time")
            )
        if e.code == 21610:
            raise TransportRecipientError(_("This phone number has been blocked"))
        if e.code == 21614:
            raise TransportRecipientError(
                _("This phone number cannot receive SMS messages")
            )
        raise TransportTransactionError("Twilio API Error", e.code, e.msg)


senders_by_prefix = [('+91', send_via_exotel), ('+', send_via_twilio)]


def send(phone: str, message: str, callback: bool = True) -> str:
    """
    Send an SMS message to a given phone number and return a transaction id

    :param phone_number: Phone number
    :param message: Message to deliver to phone number
    :param callback: Whether to request a status callback
    :return: Transaction id
    """
    for prefix, sender in senders_by_prefix:
        if phone.startswith(prefix):
            return sender(phone, message, callback)
    raise TransportRecipientError("No service provider available for this recipient")
