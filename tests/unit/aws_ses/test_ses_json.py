import json
import os

from funnel.aws_ses import SesEvent, Validator, ValidatorException, ValidatorChecks


class TestSesEventJson:

    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')

    def test_delivery(self) -> None:
        """
        Checks if the Data classes are parsed correctly.
        :return: None
        """
        with open(os.path.join(self.data_dir, "delivery.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        assert obj.eventType == "Delivery"
        assert obj.mail.tags
        assert obj.mail.timestamp
        assert obj.mail.source
        assert obj.mail.commonHeaders
        assert obj.mail.destination
        assert obj.mail.headers
        assert obj.mail.sendingAccountId
        assert obj.mail.sourceArn
        assert obj.delivery.timestamp
        assert obj.delivery.recipients
        assert obj.delivery.reportingMTA
        assert obj.delivery.smtpResponse
        assert obj.delivery.processingTimeMillis

    def test_bounce(self) -> None:
        """
        Checks if Data classes for bounce is parsed correctly
        :return: None
        """
        with open(os.path.join(self.data_dir, "bounce.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        assert obj.bounce
        assert obj.bounce.is_hard_bounce()
        assert len(obj.bounce.bouncedRecipients) == 1
        assert obj.bounce.bounceSubType == "General"
        assert obj.bounce.feedbackId
        assert obj.bounce.timestamp
        assert obj.bounce.reportingMTA

    def test_complaint(self) -> None:
        """
        Checks if Data classes for complaint is parsed correctly
        :return: None
        """
        with open(os.path.join(self.data_dir, "complaint.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        assert obj.complaint
        assert obj.complaint.feedbackId
        assert obj.complaint.complaintSubType is None
        assert obj.complaint.arrivalDate
        assert len(obj.complaint.complainedRecipients) == 1
        assert obj.complaint.complaintFeedbackType == "abuse"
        assert obj.complaint.userAgent == "Amazon SES Mailbox Simulator"

    def test_signature_good_message(self) -> None:
        """
        Checks if Signature Verification works.
        :return None:
        """
        with open(os.path.join(self.data_dir, "full-message.json"), 'r') as file:
            data = file.read()

        # Decode the JSON
        message = json.loads(data)
        validator = Validator(["arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com"])

        # Checks
        validator.check(message, ValidatorChecks.SIGNATURE)
        validator.check(message, ValidatorChecks.SIGNATURE_VERSION)
        validator.check(message, ValidatorChecks.CERTIFICATE_URL)
        validator.check(message, ValidatorChecks.TOPIC)

    def test_signature_bad_message(self) -> None:
        """
        Checks if Signature Verification works.
        :return None:
        """
        with open(os.path.join(self.data_dir, "bad-message.json"), 'r') as file:
            data = file.read()

        # Decode the JSON
        message = json.loads(data)
        validator = Validator(["arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com"])

        # Checks
        validator.check(message, ValidatorChecks.SIGNATURE_VERSION)
        validator.check(message, ValidatorChecks.CERTIFICATE_URL)
        validator.check(message, ValidatorChecks.TOPIC)
        try:
            validator.check(message, ValidatorChecks.SIGNATURE)
            assert False
        except ValidatorException:
            assert True
