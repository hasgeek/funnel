from types import SimpleNamespace

from .. import app
from . import email, sms, telegram, webpush, whatsapp

__all__ = ['email', 'sms', 'webpush', 'telegram', 'whatsapp', 'platform_transports']

#: List of available transports as platform capabilities. Each is turned on by
#: :func:`init` if the necessary functionality and config exist. Views may consult this
#: when exposing transport availability to users.
platform_transports = SimpleNamespace(
    email=False, sms=False, webpush=False, telegram=False, whatsapp=False
)


def init():
    if app.config.get('MAIL_SERVER'):
        platform_transports.email = True
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
        # TODO: Change this to turn on when transactional SMS infra is ready
        platform_transports.sms = True
    # Other transports are not supported yet
