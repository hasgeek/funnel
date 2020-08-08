import json
import os

from flask import Response


class TestSESNotices(object):
    """
    Tests SES Notices
    """

    # Data Directory which contains JSON Files
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

    # URL
    URL = '/api/1/email/ses_event'

    def test_invalid_method(self, test_client):
        """
        Tests Get Message which is Invalid as only Posts are allowed.
        """
        with test_client as c:
            resp: Response = c.get(TestSESNotices.URL)
        assert resp.status_code == 405

    def test_empty_json(self, test_client):
        """
        Test Empty JSON
        """
        with test_client as c:
            resp: Response = c.post(TestSESNotices.URL)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['status'] == 'error'

    def test_bad_message(self, test_client):
        """
        Test Bad Message
        """
        with open(
            os.path.join(TestSESNotices.DATA_DIR, "bad-message.json"), 'r'
        ) as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(TestSESNotices.URL, json=json.loads(data))
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['status'] == 'error'
        assert data['message'] == ['Signature mismatch.']

    def test_complaint_message(self, test_client, test_db_structure):
        """
        Test complaint message
        """
        with open(
            os.path.join(TestSESNotices.DATA_DIR, "full-message.json"), 'r'
        ) as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(TestSESNotices.URL, json=json.loads(data))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'Success'

    def test_delivery_message(self, test_client, test_db_structure):
        """
        Test Delivery message
        """
        with open(
            os.path.join(TestSESNotices.DATA_DIR, "delivery-message.json"), 'r'
        ) as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(TestSESNotices.URL, json=json.loads(data))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'Success'
        test_db_structure.session.commit()

    def test_bounce_message(self, test_client, test_db_structure):
        """
        Test Bounce Message
        """
        with open(
            os.path.join(TestSESNotices.DATA_DIR, "bounce-message.json"), 'r'
        ) as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(TestSESNotices.URL, json=json.loads(data))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'Success'
        test_db_structure.session.commit()
