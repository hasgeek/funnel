import json
import os
import unittest

from funnel.util.aws_ses import SesEvent, Validator, ValidatorChecks, ValidatorException


class SesEventJsonTest(unittest.TestCase):

    def setUp(self) -> None:
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../../aws_ses/tests/data')

    def test_delivery(self) -> None:
        """
        Checks if the Data classes are parsed correctly.
        :return: None
        """
        with open(os.path.join(self.data_dir, "delivery.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        self.assertEqual(obj.eventType, "Delivery")
        self.assertIsNotNone(obj.mail.timestamp)
        self.assertIsNotNone(obj.mail.tags)
        self.assertIsNotNone(obj.mail.source)
        self.assertIsNotNone(obj.mail.commonHeaders)
        self.assertIsNotNone(obj.mail.destination)
        self.assertIsNotNone(obj.mail.headers)
        self.assertIsNotNone(obj.mail.sendingAccountId)
        self.assertIsNotNone(obj.mail.sourceArn)
        self.assertIsNotNone(obj.delivery.timestamp)
        self.assertIsNotNone(obj.delivery.recipients)
        self.assertIsNotNone(obj.delivery.reportingMTA)
        self.assertIsNotNone(obj.delivery.smtpResponse)
        self.assertIsNotNone(obj.delivery.processingTimeMillis)

    def test_bounce(self) -> None:
        """
        Checks if Data classes for bounce is parsed correctly
        :return: None
        """
        with open(os.path.join(self.data_dir, "bounce.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        self.assertIsNotNone(obj.bounce)
        self.assertEqual(obj.bounce.is_hard_bounce(), True)
        self.assertEqual(obj.bounce.bounceSubType, "General")
        self.assertEqual(len(obj.bounce.bouncedRecipients), 1)
        self.assertIsNotNone(obj.bounce.feedbackId)
        self.assertIsNotNone(obj.bounce.timestamp)
        self.assertIsNotNone(obj.bounce.reportingMTA)

    def test_complaint(self) -> None:
        """
        Checks if Data classes for complaint is parsed correctly
        :return: None
        """
        with open(os.path.join(self.data_dir, "complaint.json"), 'r') as file:
            data = file.read()
        obj: SesEvent = SesEvent.from_json(data)
        self.assertIsNotNone(obj.complaint)
        self.assertIsNotNone(obj.complaint.feedbackId)
        self.assertEqual(obj.complaint.complaintFeedbackType, "abuse")
        self.assertEqual(obj.complaint.userAgent, "Amazon SES Mailbox Simulator")
        self.assertEqual(len(obj.complaint.complainedRecipients), 1)
        self.assertIsNone(obj.complaint.complaintSubType)
        self.assertIsNotNone(obj.complaint.arrivalDate)

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
            self.assertTrue(False)
        except ValidatorException:
            self.assertTrue(True)
