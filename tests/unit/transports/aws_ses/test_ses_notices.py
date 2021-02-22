import os

from flask import Response


class TestSESNotices:
    """Tests SES Notices."""

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
        rdata = resp.get_json()
        assert rdata['status'] == 'error'
