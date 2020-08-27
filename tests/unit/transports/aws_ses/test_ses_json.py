import json
import os

import pytest

from funnel.transports.email.aws_ses import (
    SesEvent,
    SnsValidator,
    SnsValidatorChecks,
    SnsValidatorException,
)


class TestSesEventJson:
    # Data Directory which contains JSON Files
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    def test_delivery(self) -> None:
        """
        Checks if the Data classes are parsed correctly.
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
        assert obj.delivery.timestamp
        assert obj.delivery.recipients
        assert obj.delivery.reporting_mta
        assert obj.delivery.smtp_response
        assert obj.delivery.processing_time

    def test_bounce(self) -> None:
        """
        Checks if Data classes for bounce is parsed correctly
        :return: None
        """
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
        """
        Checks if Data classes for complaint is parsed correctly
        :return: None
        """
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

    def test_signature_good_message(self) -> None:
        """
        Checks if Signature Verification works.
        :return None:
        """
        with open(os.path.join(self.data_dir, "full-message.json"), 'r') as file:
            data = file.read()

        # Decode the JSON
        message = json.loads(data)
        validator = SnsValidator(
            ["arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com"]
        )

        # Checks
        validator.check(message, SnsValidatorChecks.SIGNATURE)
        validator.check(message, SnsValidatorChecks.SIGNATURE_VERSION)
        validator.check(message, SnsValidatorChecks.CERTIFICATE_URL)
        validator.check(message, SnsValidatorChecks.TOPIC)

    def test_signature_bad_message(self) -> None:
        """
        Checks if Signature Verification works.
        :return None:
        """
        with open(os.path.join(self.data_dir, "bad-message.json"), 'r') as file:
            data = file.read()

        # Decode the JSON
        message = json.loads(data)
        validator = SnsValidator(
            ["arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com"]
        )

        # Checks
        validator.check(message, SnsValidatorChecks.SIGNATURE_VERSION)
        validator.check(message, SnsValidatorChecks.CERTIFICATE_URL)
        validator.check(message, SnsValidatorChecks.TOPIC)
        with pytest.raises(SnsValidatorException):
            validator.check(message, SnsValidatorChecks.SIGNATURE)
