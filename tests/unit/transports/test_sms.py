import os

from flask import Response

from funnel.transports.base import TransportTransactionError
from funnel.transports.sms import send

# Target Numbers (Test Only). See this
# https://www.twilio.com/docs/iam/test-credentials
TWILIO_CLEAN_TARGET = "+15005550010"
TWILIO_INVALID_TARGET = "+15005550001"
TWILIO_CANT_ROUTE = "+15005550002"
TWILIO_NO_SMS_SERVICE = "+15005550009"

# Dummy Message
MESSAGE = "Test Message"


def test_twilio_success():
    """ Test if Message sending is a success. """
    sid = send(TWILIO_CLEAN_TARGET, MESSAGE, callback=False)
    assert sid


def test_twilio_callback():
    """ Test if Message sending is a success. """
    sid = send(TWILIO_CLEAN_TARGET, MESSAGE, callback=True)
    assert sid


def test_twilio_failures():
    """ Test if message sending is a failure """

    # Invalid Target
    try:
        send(TWILIO_INVALID_TARGET, MESSAGE, callback=False)
        assert False
    except TransportTransactionError:
        assert True

    # Cant route
    try:
        send(TWILIO_CANT_ROUTE, MESSAGE, callback=False)
        assert False
    except TransportTransactionError:
        assert True

    # No SMS Service
    try:
        send(TWILIO_NO_SMS_SERVICE, MESSAGE, callback=False)
        assert False
    except TransportTransactionError:
        assert True


class TestTwilioCallback:
    """ Tests for Twilio SMS Callback """

    # Data Directory which contains JSON Files
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # URL
    URL = 'api/1/sms/twilio_event'

    # Dummy headers. Or else tests will start failing
    HEADERS = {'X-Twilio-Signature': 'Random Signature'}

    def test_missing_header(self, test_client):
        """ Check for Missing Twilio header and GET Methods. """

        # GET requests are not allowed.
        with test_client as c:
            resp: Response = c.get(self.URL)
        assert resp.status_code == 405

        # Missing Twilio headers
        with test_client as c:
            resp: Response = c.post(self.URL)
            data = resp.get_json()
        assert resp.status_code == 400
        assert data['status'] == 'error'

    def test_missing_json(self, test_client):
        """ Test for Missing JSON Payload """
        with test_client as c:
            resp: Response = c.post(self.URL)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['status'] == 'error'

    def test_bad_message(self, test_client):
        """ Test for bad json message """
        with open(os.path.join(self.data_dir, "twilio_sms.json"), 'r') as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(self.URL, json=data, headers=self.HEADERS)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['status'] == 'error'
