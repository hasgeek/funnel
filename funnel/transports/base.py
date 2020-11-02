from typing import Dict

from .. import app

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


class TransportError(Exception):
    """Base class for transport exceptions."""


class TransportConnectionError(TransportError):
    """Transport engine was unavailable."""


class TransportRecipientError(TransportError):
    """Transport engine did not accept the recipient."""


class TransportTransactionError(TransportError):
    """Transport engine did not accept payload."""


def init():
    if app.config.get('MAIL_SERVER'):
        platform_transports['email'] = True
    if all(
        app.config.get(var)
        for var in (
            'SMS_EXOTEL_SID',
            'SMS_EXOTEL_TOKEN',
            'SMS_TWILIO_SID',
            'SMS_TWILIO_TOKEN',
            'SMS_TWILIO_FROM',
        )
    ):
        platform_transports['sms'] = True

    # Other transports are not supported yet
