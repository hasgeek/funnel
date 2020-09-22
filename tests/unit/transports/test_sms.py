from funnel.transports.base import TransportRecipientError
from funnel.transports.sms import send

# Target Numbers (Test Only). See this
# https://www.twilio.com/docs/iam/test-credentials
TWILIO_CLEAN_TARGET = "+15005550010"
TWILIO_INVALID_TARGET = "+15005550001"
TWILIO_CANT_ROUTE = "+15005550002"
TWILIO_NO_SMS_SERVICE = "+15005550009"

# Dummy Message
MESSAGE = "Test Message"


def test_twilio_success(test_client):
    """Test if message sending is a success."""
    sid = send(TWILIO_CLEAN_TARGET, MESSAGE, callback=False)
    assert sid


def test_twilio_callback(test_client):
    """Test if message sending is a success when a callback is requested."""
    sid = send(TWILIO_CLEAN_TARGET, MESSAGE, callback=True)
    assert sid


def test_twilio_failures(test_client):
    """Test if message sending is a failure."""

    # Invalid Target
    try:
        send(TWILIO_INVALID_TARGET, MESSAGE, callback=False)
        assert False
    except TransportRecipientError:
        assert True

    # Cant route
    try:
        send(TWILIO_CANT_ROUTE, MESSAGE, callback=False)
        assert False
    except TransportRecipientError:
        assert True

    # No SMS Service
    try:
        send(TWILIO_NO_SMS_SERVICE, MESSAGE, callback=False)
        assert False
    except TransportRecipientError:
        assert True
