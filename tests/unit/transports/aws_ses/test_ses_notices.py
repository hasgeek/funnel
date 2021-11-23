from typing import cast
import json
import os

from flask import Response

# Data Directory which contains JSON Files
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# URL
URL = '/api/1/email/ses_event'

# Dummy headers. Or else tests will start failing
HEADERS = {
    'x-amz-sns-message-type': 'Not Empty',
    'x-amz-sns-message-id': 'Some ID',
    'x-amz-sns-topic-arn': 'Some Topic',
}


def test_invalid_method(client) -> None:
    """GET requests are not allowed."""
    resp: Response = client.get(URL)
    assert resp.status_code == 405


def test_empty_json(client) -> None:
    """Test empty JSON."""
    resp: Response = client.post(URL)
    assert resp.status_code == 422
    rdata = cast(dict, resp.get_json())
    assert rdata['status'] == 'error'


# FIXME: Test certificate has expired
def fixme_test_bad_message(client) -> None:
    """Test bad signature message."""
    with open(os.path.join(DATA_DIR, 'bad-message.json')) as file:
        data = file.read()
    resp: Response = client.post(URL, json=json.loads(data), headers=HEADERS)
    assert resp.status_code == 422
    rdata = cast(dict, resp.get_json())
    assert rdata['status'] == 'error'
    assert rdata['error'] == 'validation_failure'


# FIXME: Test certificate has expired
def fixme_test_complaint_message(client):
    """Test Complaint message."""
    with open(os.path.join(DATA_DIR, 'full-message.json')) as file:
        data = file.read()
    resp: Response = client.post(URL, json=json.loads(data), headers=HEADERS)
    assert resp.status_code == 200
    rdata = resp.get_json()
    assert rdata['status'] == 'ok'


# FIXME: Test certificate has expired
def fixme_test_delivery_message(client):
    """Test Delivery message."""
    with open(os.path.join(DATA_DIR, 'delivery-message.json')) as file:
        data = file.read()
    resp: Response = client.post(URL, json=json.loads(data), headers=HEADERS)
    assert resp.status_code == 200
    rdata = resp.get_json()
    assert rdata['status'] == 'ok'


# FIXME: Test certificate has expired
def fixme_test_bounce_message(client):
    """Test Bounce message."""
    with open(os.path.join(DATA_DIR, 'bounce-message.json')) as file:
        data = file.read()
    resp: Response = client.post(URL, json=json.loads(data), headers=HEADERS)
    assert resp.status_code == 200
    rdata = resp.get_json()
    assert rdata['status'] == 'ok'
