"""Initialization for supported transports."""

from __future__ import annotations

from typing import Dict

from .. import app
from .sms import SmsTemplate

#: List of available transports as platform capabilities. Each is turned on by
#: :func:`init` if the necessary functionality and config exist. Views may consult this
#: when exposing transport availability to users.
platform_transports: Dict[str, bool] = {
    'email': False,
    'sms': False,
    'webpush': False,
    'telegram': False,
    'whatsapp': False,
}


def init():
    if app.config.get('MAIL_SERVER'):
        platform_transports['email'] = True
    if all(
        app.config.get(var)
        for var in (
            'SMS_EXOTEL_SID',
            'SMS_EXOTEL_TOKEN',
            'SMS_DLT_ENTITY_ID',
            'SMS_TWILIO_SID',
            'SMS_TWILIO_TOKEN',
            'SMS_TWILIO_FROM',
        )
    ):
        platform_transports['sms'] = True
        SmsTemplate.init_app(app)

    # Other transports are not supported yet
