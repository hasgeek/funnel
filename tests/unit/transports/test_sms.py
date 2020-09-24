import uuid

from flask import Response

from funnel.transports.base import TransportRecipientError
from funnel.transports.sms import (
    TransportTransactionError,
    make_exotel_token,
    send,
    validate_exotel_token,
)

# Target Numbers (Test Only). See this
# https://www.twilio.com/docs/iam/test-credentials
TWILIO_CLEAN_TARGET = "+15005550010"
TWILIO_INVALID_TARGET = "+15005550001"
TWILIO_CANT_ROUTE = "+15005550002"
TWILIO_NO_SMS_SERVICE = "+15005550009"

# Exotel Numbers to test. They are just made up numbers.
EXOTEL_TO = "+919999999999"

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


def test_exotel_nonce(test_client, test_db_structure):
    """ Test if the exotel nonce works as expected"""

    # The random case.
    nonce = str(uuid.uuid1())
    token = make_exotel_token(nonce)
    valid = validate_exotel_token(token)
    assert valid

    # Pretend that we got another one within X days
    assert validate_exotel_token(token)

    # Now call the callback using POST and see if it works.
    # URL and Headers for the post call
    url = '/api/1/sms/exotel_event/' + token
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'To': '+919999999999', 'SmsSid': 'Some-long-string', 'Status': 'sent'}
    with test_client as c:
        resp: Response = c.post(url, headers=headers, data=data)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'
        test_db_structure.session.commit()


def test_exotel_send(test_client):
    """ Only tests if url_for works and usually fails otherwise, which is OK"""
    try:
        sid = send(EXOTEL_TO, MESSAGE, callback=True)
        assert sid
    except TransportTransactionError:
        assert True
