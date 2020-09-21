"""Support functions for sending a short text message."""

from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import config, dataclass_json
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
import requests

from .. import app
from .base import (
    TransportConnectionError,
    TransportRecipientError,
    TransportTransactionError,
)

__all__ = ['send', 'TwilioSmsResponse', 'send_via_exotel', 'send_via_twilio']


@dataclass_json
@dataclass
class TwilioSmsResponse:
    """
    SMS Status Message sent by Twilio for processing. See this for more information
    https://www.twilio.com/docs/sms/send-messages

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


def send(phone_number: str, message: str, callback: bool = True) -> str:
    """
    Send the message to a given phone number based on internal rules.

    :param phone_number: Phone Number
    :param message: Message to deliver to Phone number.
    :param callback: URL Callback for status updates
    :return: SMS Message ID
    """
    if phone_number.startswith('+91'):
        return send_via_exotel(phone_number, message)
    elif phone_number.startswith('+'):
        return send_via_twilio(phone_number, message, callback)
    raise TransportRecipientError("No service provider available for this recipient")


def send_via_exotel(phone_number: str, message: str) -> str:
    """
    Route the SMS via Exotel. This is done only for messages that can't be delivered by Twilio.

    :param phone_number: Phone Number
    :param message: Message to deliver to Phone number.
    :return: SMS Message ID
    """
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


def send_via_twilio(phone: str, message: str, callback: bool = True) -> str:
    """
    Route the SMS via Twilio

    :param phone: Phone Number
    :param message: Message to deliver to Phone number.
    :param callback: URL Callback for status updates
    :return: SMS Message ID
    """
    # Get SID, Token and From (these are required to make any calls)
    account = app.config['SMS_TWILIO_SID']
    token = app.config['SMS_TWILIO_TOKEN']
    sender = app.config['SMS_TWILIO_FROM']

    # Call back if needed.
    url_callback = None
    if callback:
        url_callback = app.config['SMS_TWILIO_CALLBACK']

    # Send (This uses the routing API to deliver SMS via a Low Latency Location).
    # See https://www.twilio.com/docs/global-infrastructure/edge-locations
    client = Client(account, token)

    # Error evaluation is needed as API may fail for a variety of reasons.
    try:
        msg = client.messages.create(
            from_=sender,
            to=phone,
            body=message,
            status_callback=url_callback,
        )
        return msg.sid
    except TwilioRestException as e:
        raise TransportTransactionError("Twilio API Error", e.code, e.msg)
