import os

from flask import Response

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


# Data Directory which contains JSON Files
data_dir = os.path.join(os.path.dirname(__file__), 'data')

# URL
URL = '/api/1/sms/twilio_event'

# Dummy headers. Or else tests will start failing
HEADERS = {
    'X-Twilio-Signature': "Random Signature",
    'Content-Type': 'application/x-www-form-urlencoded',
}


def test_missing_header(test_client):
    """Check for missing Twilio header and GET methods."""

    # GET requests are not allowed.
    with test_client as c:
        resp: Response = c.get(URL)
    assert resp.status_code == 405

    # Missing Twilio headers
    with test_client as c:
        resp: Response = c.post(URL)
        data = resp.get_json()
    assert resp.status_code == 422
    assert data['status'] == 'error'


def test_missing_json(test_client):
    """Test for Missing JSON payload."""
    with test_client as c:
        resp: Response = c.post(URL)
    assert resp.status_code == 422
    data = resp.get_json()
    assert data['status'] == 'error'


def test_bad_message(test_client):
    """Test for bad JSON message."""
    with open(os.path.join(data_dir, 'twilio_sms.json'), 'r') as file:
        data = file.read()
    with test_client as c:
        resp: Response = c.post(URL, data=data, headers=HEADERS)
    assert resp.status_code == 422
    data = resp.get_json()
    assert data['status'] == 'error'
