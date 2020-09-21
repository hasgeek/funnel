from flask import url_for

from .. import app

#: List of available transports as platform capabilities. Each is turned on by
#: :func:`init` if the necessary functionality and config exist. Views may consult this
#: when exposing transport availability to users.
platform_transports = {
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

    # We need to set Callback URL for SMS notifications here as there are two different providers
    # (Exotel and Twilio) and both of them need different URLs as the schema is very different.
    with app.app_context():
        app.config['SMS_TWILIO_CALLBACK'] = url_for(
            'process_twilio_event', _external=True, _method='POST'
        )

        # FiXME: Only for reference. Will be gone by next commit when exotel support is added.
        app.config['SMS_EXOTEL_CALLBACK'] = url_for(
            'process_exotel_event', _external=True, _method='POST'
        )

    # Other transports are not supported yet
