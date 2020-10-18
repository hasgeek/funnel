import json
import os

from flask import Response


class TestSESNotices:
    """ Tests SES Notices """

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

    def test_invalid_method(self, test_client) -> None:
        """GET requests are not allowed."""
        with test_client as c:
            resp: Response = c.get(self.URL)
        assert resp.status_code == 405

    def test_empty_json(self, test_client) -> None:
        """Test empty JSON."""
        with test_client as c:
            resp: Response = c.post(self.URL)
        assert resp.status_code == 422
        data = resp.get_json()
        assert data['status'] == 'error'

    def test_bad_message(self, test_client) -> None:
        """Test bad signature message."""
        with open(os.path.join(self.DATA_DIR, "bad-message.json"), 'r') as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(
                self.URL, json=json.loads(data), headers=self.HEADERS
            )
        assert resp.status_code == 422
        data = resp.get_json()
        assert data['status'] == 'error'
        assert data['message'] == ['Signature mismatch']

    def test_complaint_message(self, test_client, test_db_structure):
        """Test Complaint message."""
        with open(os.path.join(self.DATA_DIR, "full-message.json"), 'r') as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(
                self.URL, json=json.loads(data), headers=self.HEADERS
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'

    def test_delivery_message(self, test_client, test_db_structure):
        """Test Delivery message."""
        with open(os.path.join(self.DATA_DIR, "delivery-message.json"), 'r') as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(
                self.URL, json=json.loads(data), headers=self.HEADERS
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'
        test_db_structure.session.commit()

    def test_bounce_message(self, test_client, test_db_structure):
        """Test Bounce message."""
        with open(os.path.join(self.DATA_DIR, "bounce-message.json"), 'r') as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(
                self.URL, json=json.loads(data), headers=self.HEADERS
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'
        test_db_structure.session.commit()
