import os

from funnel.transports.email.aws_ses import SesEvent


class TestSesEventJson:
    # Data Directory which contains JSON Files
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    def test_delivery(self) -> None:
        """
        Check if the Data classes are parsed correctly.

        :return: None
        """
        with open(os.path.join(self.data_dir, "delivery.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        assert obj.event_type == "Delivery"
        assert obj.mail.tags
        assert obj.mail.timestamp
        assert obj.mail.source
        assert obj.mail.common_headers
        assert obj.mail.destination
        assert obj.mail.headers
        assert obj.mail.sending_accountid
        assert obj.mail.source_arn
        assert obj.delivery
        assert obj.delivery.timestamp
        assert obj.delivery.recipients
        assert obj.delivery.reporting_mta
        assert obj.delivery.smtp_response
        assert obj.delivery.processing_time

    def test_bounce(self) -> None:
        """Check if Data classes for bounce is parsed correctly."""
        with open(os.path.join(self.data_dir, "bounce.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        assert obj.bounce
        assert obj.bounce.is_hard_bounce is True
        assert len(obj.bounce.bounced_recipients) == 1
        assert obj.bounce.bounce_sub_type == "General"
        assert obj.bounce.feedbackid
        assert obj.bounce.timestamp
        assert obj.bounce.reporting_mta

    def test_complaint(self) -> None:
        """Check if Data classes for complaint is parsed correctly."""
        with open(os.path.join(self.data_dir, "complaint.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        assert obj.complaint
        assert obj.complaint.feedbackid
        assert obj.complaint.complaint_sub_type is None
        assert obj.complaint.arrival_date
        assert len(obj.complaint.complained_recipients) == 1
        assert obj.complaint.complaint_feedback_type == "abuse"
        assert obj.complaint.user_agent == "Amazon SES Mailbox Simulator"
