"""Tests for sending SMS."""

from datetime import datetime
from unittest.mock import patch

import pytest
import requests
from flask import Response
from pytz import utc

from funnel.transports import TransportConnectionError, TransportRecipientError
from funnel.transports.sms import (
    WebOtpTemplate,
    make_exotel_token,
    send_sms,
    validate_exotel_token,
)
from funnel.transports.sms.send import (
    indian_timezone,
    okay_to_message_in_india_right_now,
)

# Target Numbers (Test Only). See this
# https://www.twilio.com/docs/iam/test-credentials
TWILIO_CLEAN_TARGET = "+15005550010"
TWILIO_INVALID_TARGET = "+15005550001"
TWILIO_CANT_ROUTE = "+15005550002"
TWILIO_NO_SMS_SERVICE = "+15005550009"

# Exotel Numbers to test. They are just made up numbers.
EXOTEL_TO = "+919999999999"
# Exotel callbacks use zero-prefixed numbers
EXOTEL_CALLBACK_TO = "09999999999"

# Dummy Message
MESSAGE = WebOtpTemplate(otp="1234")


@pytest.mark.enable_socket()
@pytest.mark.requires_config('app', 'twilio')
@pytest.mark.usefixtures('app_context')
def test_twilio_success() -> None:
    """Test if message sending is a success."""
    sid = send_sms(TWILIO_CLEAN_TARGET, MESSAGE, callback=False)
    assert sid


@pytest.mark.enable_socket()
@pytest.mark.requires_config('app', 'twilio')
@pytest.mark.usefixtures('app_context')
def test_twilio_callback() -> None:
    """Test if message sending is a success when a callback is requested."""
    sid = send_sms(TWILIO_CLEAN_TARGET, MESSAGE, callback=True)
    assert sid


@pytest.mark.enable_socket()
@pytest.mark.requires_config('app', 'twilio')
@pytest.mark.usefixtures('app_context')
def test_twilio_failures() -> None:
    """Test if message sending is a failure."""
    # Invalid Target
    with pytest.raises(TransportRecipientError):
        send_sms(TWILIO_INVALID_TARGET, MESSAGE, callback=False)

    # Can't route
    with pytest.raises(TransportRecipientError):
        send_sms(TWILIO_CANT_ROUTE, MESSAGE, callback=False)

    # No SMS Service
    with pytest.raises(TransportRecipientError):
        send_sms(TWILIO_NO_SMS_SERVICE, MESSAGE, callback=False)


def test_exotel_nonce(client) -> None:
    """Test if the exotel nonce works as expected."""
    # Make a token
    token = make_exotel_token(EXOTEL_TO)
    assert validate_exotel_token(token, EXOTEL_TO)
    # A second callback will pass as it's a signed token and usage is not tracked
    assert validate_exotel_token(token, EXOTEL_TO)

    # Make a fresh token and test the view
    token = make_exotel_token(EXOTEL_TO)
    # Now call the callback using POST and see if it works.
    # URL and Headers for the post call
    url = '/api/1/sms/exotel_event/' + token
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'To': EXOTEL_CALLBACK_TO, 'SmsSid': 'Some-long-string', 'Status': 'sent'}
    resp: Response = client.post(url, headers=headers, data=data)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'


@pytest.mark.requires_config('app', 'exotel')
@pytest.mark.usefixtures('app_context', 'db_session')
@patch.object(WebOtpTemplate, 'registered_templateid', 'test')
def test_exotel_send_error() -> None:
    """Only tests if url_for works and usually fails otherwise, which is OK."""
    # Check False Path via monkey patching the requests object
    with patch.object(requests, 'post') as mock_method:
        mock_method.side_effect = requests.ConnectionError
        with pytest.raises(TransportConnectionError):
            send_sms(EXOTEL_TO, MESSAGE, callback=True)


@pytest.mark.parametrize(
    ('now', 'okay'),
    [
        (indian_timezone.localize(datetime(2020, 1, 1, 8, 59)).astimezone(utc), False),
        (indian_timezone.localize(datetime(2020, 1, 1, 9, 0)).astimezone(utc), True),
        (indian_timezone.localize(datetime(2020, 1, 1, 12, 0)).astimezone(utc), True),
        (indian_timezone.localize(datetime(2020, 1, 1, 16, 0)).astimezone(utc), True),
        (indian_timezone.localize(datetime(2020, 1, 1, 18, 0)).astimezone(utc), True),
        (indian_timezone.localize(datetime(2020, 1, 1, 18, 59)).astimezone(utc), True),
        (indian_timezone.localize(datetime(2020, 1, 1, 19, 0)).astimezone(utc), False),
        (indian_timezone.localize(datetime(2020, 1, 1, 21, 0)).astimezone(utc), False),
    ],
)
def test_okay_to_message_in_india_right_now(now: datetime, okay: bool) -> None:
    """Confirm validator says its okay to message between 9 AM and 7 PM IST."""
    with patch('funnel.transports.sms.send.utcnow', return_value=now):
        assert okay_to_message_in_india_right_now() is okay
        nowin = now.astimezone(indian_timezone)
        if okay:
            assert 9 <= nowin.hour < 19
        else:
            assert nowin.hour >= 19 or nowin.hour < 9
