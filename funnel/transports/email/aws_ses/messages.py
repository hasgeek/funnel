"""This module contains SES message types, as received over SNS."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from dataclasses_json import config, dataclass_json

__all__ = [
    'Bounce',
    'Complaint',
    'Delivery',
    'DeliveryDelay',
    'SesEvent',
    'SesProcessorAbc',
]


@dataclass_json
@dataclass
class MailHeaders:
    """Mail Headers have name/value pairs."""

    name: str
    value: str


@dataclass_json
@dataclass
class CommonMailHeaders:
    """Json object for common mail headers."""

    from_address: List[str] = field(metadata=config(field_name='from'))
    to_address: List[str] = field(metadata=config(field_name='to'))
    subject: str
    messageid: str = field(metadata=config(field_name='messageId'))


@dataclass_json
@dataclass
class Mail:
    """
    The JSON object that contains information about a mail object.

    * timestamp: The date and time, in ISO8601 format
    * messageid: A unique ID that Amazon SES assigned to the message.
    * source: The email address that the message was sent from
    * source_arn: The Amazon Resource Name (ARN) of the identity that was used
    * sending_accountid: The AWS account ID of the account
    * destination: A list of email addresses that were recipients of the original mail
    * headers_truncated: Are headers truncated?
    * headers: A list of the email's original headers.
    * common_headers: A list of the email's original, commonly used headers.
    * tags: SES tags with list of values per tag
    """

    timestamp: str
    messageid: str = field(metadata=config(field_name='messageId'))
    source: str
    source_arn: str = field(metadata=config(field_name='sourceArn'))
    sending_accountid: str = field(metadata=config(field_name='sendingAccountId'))
    destination: List[str]
    headers_truncated: bool = field(metadata=config(field_name='headersTruncated'))
    headers: List[MailHeaders]
    common_headers: CommonMailHeaders = field(
        metadata=config(field_name='commonHeaders')
    )
    tags: Dict[str, List[str]]


@dataclass_json
@dataclass
class IndividualRecipient:
    """
    Individual recipient for whom the email message bounced.

    * email: Email Address
    * action: Action (mostly "failed")
    * status: Numeric status in string format
    * diagnostic_code: SMTP diagnostic code
    """

    email: str = field(metadata=config(field_name='emailAddress'))
    action: Optional[str] = None
    status: Optional[str] = None
    diagnostic_code: Optional[str] = field(
        metadata=config(field_name='diagnosticCode'), default=None
    )


@dataclass_json
@dataclass
class Bounce:
    """
    The JSON object that contains information about a Bounce event.

    * bounce_type: The type of bounce
    * bounce_sub_type: The subtype of the bounce
    * bounced_recipients: List of recipients for whom the email bounced
    * timestamp: The date and time, in ISO8601 format
    * feedbackid: A unique ID for the bounce
    * reporting_mta: The value of the Reporting-MTA field from the DSN. This is the
        value of the Message Transfer Authority (MTA) that attempted to perform the
        delivery, relay, or gateway operation described in the DSN.
    """

    bounce_type: str = field(metadata=config(field_name='bounceType'))
    bounce_sub_type: str = field(metadata=config(field_name='bounceSubType'))
    bounced_recipients: List[IndividualRecipient] = field(
        metadata=config(field_name='bouncedRecipients')
    )
    timestamp: str
    feedbackid: str = field(metadata=config(field_name='feedbackId'))
    reporting_mta: Optional[str] = field(
        metadata=config(field_name='reportingMTA'), default=None
    )

    @property
    def is_hard_bounce(self) -> bool:
        """
        Check if Bounce message is a hard bounce.
        If you receive this type of bounce, you should remove the
        recipient's email address from your mailing list.
        :return: True if it is hard bounce, false if not.
        """
        return self.bounce_type == 'Permanent'


@dataclass_json
@dataclass
class Complaint:
    """
    The JSON object that contains information about a Complaint event.

    * complained_recipients: Recipients that may have submitted the complaint
    * timestamp: The date and time, in ISO8601 format
    * feedbackid: A unique ID for the complaint
    * complaint_sub_type: The subtype of the complaint
    * user_agent: userAgent
    * complaint_feedback_type: This contains the type of feedback
    * arrival_date: The value of the Arrival-Date or Received-Date field

    complaint_feedback_type will have one of the following:

    * 'abuse': Indicates unsolicited email
    * 'auth-failure': Email authentication failure report
    * 'fraud': Indicates some kind of fraud or phishing activity
    * 'not-spam': Not a spam message
    * 'other': Others not belonging to any category
    * 'virus': A virus is found in the originating message
    """

    complained_recipients: List[IndividualRecipient] = field(
        metadata=config(field_name='complainedRecipients')
    )
    timestamp: str
    feedbackid: str = field(metadata=config(field_name='feedbackId'))
    complaint_sub_type: Optional[str] = field(
        metadata=config(field_name='complaintSubType'), default=None
    )
    user_agent: Optional[str] = field(
        metadata=config(field_name='userAgent'), default=None
    )
    complaint_feedback_type: Optional[str] = field(
        metadata=config(field_name='complaintFeedbackType'), default=None
    )
    arrival_date: Optional[str] = field(
        metadata=config(field_name='arrivalDate'), default=None
    )


@dataclass_json
@dataclass
class Delivery:
    """
    The JSON object that contains information about a Delivery event.

    * timestamp: The date and time
    * processing_time: Time to process and send the message, in milliseconds
    * recipients: A list of intended recipients
    * smtp_response: The SMTP response
    * reporting_mta: Host name of the Amazon SES mail server
    """

    timestamp: str
    processing_time: int = field(metadata=config(field_name='processingTimeMillis'))
    recipients: List[str]
    smtp_response: str = field(metadata=config(field_name='smtpResponse'))
    reporting_mta: str = field(metadata=config(field_name='reportingMTA'))


@dataclass_json
@dataclass
class Send:
    """ The JSON object that contains information about a Send event. Has no data."""


@dataclass_json
@dataclass
class Reject:
    """
    The JSON object that contains information about a Reject event.

    * reason: The reason the email was rejected. The only possible value is Bad content,
        which means that Amazon SES detected that the email contained a virus
    """

    reason: str


@dataclass_json
@dataclass
class Open:
    """
    The JSON object that contains information about a Open event.

    * ip_address: The recipient's IP address
    * timestamp: The date and time when the open event occurred (string)
    * user_agent: The user agent of the device or email client
    """

    ip_address: str = field(metadata=config(field_name='ipAddress'))
    timestamp: str
    user_agent: str = field(metadata=config(field_name='userAgent'))


@dataclass_json
@dataclass
class Click:
    """
    The JSON object that contains information about a Click event.

    * ip_address: The recipient's IP address.
    * timestamp: The date and time when the click event occurred
    * user_agent: The user agent of the client that the recipient
    * link: The URL of the link that the recipient clicked
    * link_tags: A list of tags that were added to the link
    """

    ip_address: str = field(metadata=config(field_name='ipAddress'))
    timestamp: str
    user_agent: str = field(metadata=config(field_name='userAgent'))
    link: str
    link_tags: Optional[Dict[str, List[str]]] = field(
        metadata=config(field_name='linkTags'), default=None
    )


@dataclass_json
@dataclass
class RenderFailure:
    """
    The JSON object that contains information about Rendering Failure event.

    * template_name: The name of the template used to send the email
    * error_message: More information about the rendering failure
    """

    template_name: str = field(metadata=config(field_name='templateName'))
    error_message: str = field(metadata=config(field_name='errorMessage'))


@dataclass_json
@dataclass
class DeliveryDelay:
    """
    The JSON object that contains information about a DeliveryDelay event.

    * delayed_recipients: Information about the recipient of the email
    * expiration_time: When Amazon SES will stop trying to deliver the message
    * reporting_mta: The IP address of the Message Transfer Agent (MTA)
    * timestamp: The date and time when the delay occurred (string)
    * delay_type: The type of delay. Possible values are:
        * 'InternalFailure': An internal Amazon SES issue caused the message to be
            delayed
        * 'General': A generic failure occurred during the SMTP conversation
        * 'MailboxFull': The recipient's mailbox is full
        * 'SpamDetected': The recipient's mail server has detected a large amount of
            SPAM
        * 'RecipientServerError': A temporary issue with the recipient's email server
        * 'IPFailure': IP address that's sending the message is being blocked or
            throttled
        * 'TransientCommunicationGeneral': Temporary communication failure
        * 'Undetermined': Amazon SES wasn't able to determine the reason
    """

    delayed_recipients: List[IndividualRecipient] = field(
        metadata=config(field_name='delayedRecipients')
    )
    expiration_time: str = field(metadata=config(field_name='expirationTime'))
    reporting_mta: str = field(metadata=config(field_name='reportingMTA'))
    timestamp: str
    delay_type: str = field(metadata=config(field_name='delayType'))


class SesEvents(Enum):
    """Types of SesEvents."""

    DELIVERY = 'Delivery'
    SEND = 'Send'
    REJECT = 'Reject'
    OPEN = 'Open'
    Click = 'Click'
    BOUNCE = 'Bounce'
    COMPLAINT = 'Complaint'
    RENDER = 'Rendering Failure'
    DELAY = 'DeliveryDelay'


@dataclass_json
@dataclass
class SesEvent:
    """
    SES Event object JSON which contains the following.

    * event_type: Possible values:
        * 'Delivery',
        * 'Send'
        * 'Reject'
        * 'Open'
        * 'Click'
        * 'Bounce'
        * 'Complaint'
        * 'Rendering Failure'
        * 'DeliveryDelay'
    * mail: A JSON object that contains information about the email
    * bounce: This field is only present if event_type is Bounce
    * complaint: This field is only present if event_type is Complaint
    * delivery: This field is only present if event_type is Delivery.
    * send: This field is only present if event_type is Send
    * reject: This field is only present if event_type is Reject
    * open: This field is only present if event_type is Open
    * click: This field is only present if event_type is Click
    * failure: This field is only present if eventType is Rendering Failure
    * delivery_delay: This field is only present if event_type is DeliveryDelay
    """

    event_type: str = field(metadata=config(field_name='eventType'))
    mail: Mail
    bounce: Optional[Bounce] = None
    complaint: Optional[Complaint] = None
    delivery: Optional[Delivery] = None
    send: Optional[Send] = None
    reject: Optional[Reject] = None
    opened: Optional[Open] = field(metadata=config(field_name='open'), default=None)
    click: Optional[Click] = None
    failure: Optional[RenderFailure] = None
    delivery_delay: Optional[DeliveryDelay] = field(
        metadata=config(field_name='deliveryDelay'), default=None
    )


class SesProcessorAbc(ABC):
    """Abstract Base class for Message Processor."""

    def process(self, ses_event: SesEvent):
        """
        Process SES Event by calling the appropriate methods.
        @param ses_event: SES Event object
        """
        if ses_event.event_type == SesEvents.BOUNCE.value:
            self.bounce(ses_event.bounce)
        elif ses_event.event_type == SesEvents.COMPLAINT.value:
            self.complaint(ses_event.complaint)
        elif ses_event.event_type == SesEvents.DELIVERY.value:
            self.delivered(ses_event.delivery)
        elif ses_event.event_type == SesEvents.DELAY.value:
            self.delayed(ses_event.delivery_delay)

    @abstractmethod
    def bounce(self, bounce: Bounce) -> None:
        """
        Process (Hard) Bounce notifications
        @param bounce: Bounce
        """

    @abstractmethod
    def complaint(self, complaint: Complaint) -> None:
        """
        Process Complaint notifications
        @param complaint: Complaint
        """

    @abstractmethod
    def delivered(self, delivery: Delivery) -> None:
        """
        Process Delivery notifications
        @param delivery: Delivery
        """

    @abstractmethod
    def delayed(self, delayed: DeliveryDelay) -> None:
        """
        Process Delivery Delay (Soft Bounce) notifications
        @param delayed: DeliveryDelay
        """
