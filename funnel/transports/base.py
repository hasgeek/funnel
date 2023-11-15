"""Initialization for supported transports."""

from __future__ import annotations

from .. import app
from .sms import init as sms_init

#: List of available transports as platform capabilities. Each is turned on by
#: :func:`init` if the necessary functionality and config exist. Views may consult this
#: when exposing transport availability to users.
platform_transports: dict[str, bool] = {
    'email': False,
    'sms': False,
    'webpush': False,
    'telegram': False,
    'whatsapp': False,
}


def init() -> None:
    if app.config.get('MAIL_SERVER'):
        platform_transports['email'] = True
    if sms_init():
        platform_transports['sms'] = True
    if app.config.get('WHATSAPP_TOKEN') and app.config.get('WHATSAPP_PHONE_ID'):
        platform_transports['whatsapp'] = True

    # Other transports are not supported yet
