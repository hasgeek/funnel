"""Test for AWS SES event handling."""

import json
import os

import pytest

from funnel.transports.email import aws_ses

# Data Directory which contains JSON Files
data_dir = os.path.join(os.path.dirname(__file__), 'data')


def test_delivery() -> None:
    """Check if the delivery JSON is parsed correctly."""
    with open(os.path.join(data_dir, 'delivery.json'), encoding='utf-8') as file:
        data = file.read()
    obj = aws_ses.SesEvent.from_json(data)
    assert obj.event_type == 'Delivery'
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


def test_delivery_without_subject() -> None:
    """Check if the delivery JSON is parsed correctly when missing a subject."""
    with open(
        os.path.join(data_dir, 'delivery-without-subject.json'),
        encoding='utf-8',
    ) as file:
        data = file.read()
    obj = aws_ses.SesEvent.from_json(data)
    assert obj.event_type == 'Delivery'
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


def test_bounce() -> None:
    """Check if Data classes for bounce is parsed correctly."""
    with open(os.path.join(data_dir, 'bounce.json'), encoding='utf-8') as file:
        data = file.read()
    obj = aws_ses.SesEvent.from_json(data)
    assert obj.bounce
    assert obj.bounce.is_hard_bounce is True
    assert len(obj.bounce.bounced_recipients) == 1
    assert obj.bounce.bounce_sub_type == 'General'
    assert obj.bounce.feedbackid
    assert obj.bounce.timestamp
    assert obj.bounce.reporting_mta


def test_complaint() -> None:
    """Check if Data classes for complaint is parsed correctly."""
    with open(os.path.join(data_dir, 'complaint.json'), encoding='utf-8') as file:
        data = file.read()
    obj = aws_ses.SesEvent.from_json(data)
    assert obj.complaint
    assert obj.complaint.feedbackid
    assert obj.complaint.complaint_sub_type is None
    assert obj.complaint.arrival_date
    assert len(obj.complaint.complained_recipients) == 1
    assert obj.complaint.complaint_feedback_type == 'abuse'
    assert obj.complaint.user_agent == 'Amazon SES Mailbox Simulator'


@pytest.mark.skip(reason="Certificate has expired")
def test_signature_good_message() -> None:
    """Check if Signature Verification works."""
    with open(os.path.join(data_dir, 'full-message.json'), encoding='utf-8') as file:
        data = file.read()

    # Decode the JSON
    message = json.loads(data)
    validator = aws_ses.SnsValidator(
        ['arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com']
    )

    # Checks
    validator.check(message, aws_ses.SnsValidatorChecks.SIGNATURE)
    validator.check(message, aws_ses.SnsValidatorChecks.SIGNATURE_VERSION)
    validator.check(message, aws_ses.SnsValidatorChecks.CERTIFICATE_URL)
    validator.check(message, aws_ses.SnsValidatorChecks.TOPIC)


@pytest.mark.skip(reason="Certificate has expired")
def test_signature_bad_message() -> None:
    """Check if Signature Verification works."""
    with open(os.path.join(data_dir, 'bad-message.json'), encoding='utf-8') as file:
        data = file.read()

    # Decode the JSON
    message = json.loads(data)
    validator = aws_ses.SnsValidator(
        ['arn:aws:sns:ap-south-1:817922165072:ses-events-for-hasgeek_dot_com']
    )

    # Checks
    validator.check(message, aws_ses.SnsValidatorChecks.SIGNATURE_VERSION)
    validator.check(message, aws_ses.SnsValidatorChecks.CERTIFICATE_URL)
    validator.check(message, aws_ses.SnsValidatorChecks.TOPIC)
    with pytest.raises(aws_ses.SnsValidatorError):
        validator.check(message, aws_ses.SnsValidatorChecks.SIGNATURE)
