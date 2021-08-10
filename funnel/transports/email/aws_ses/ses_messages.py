"""This module contains SES message types, as received over SNS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from dataclasses_json import DataClassJsonMixin, config

__all__ = [
    'SesBounce',
    'SesComplaint',
    'SesDelivery',
    'SesDeliveryDelay',
    'SesEvent',
    'SesProcessorAbc',
]


@dataclass
class SesMailHeaders(DataClassJsonMixin):
    """Mail Headers have name/value pairs."""

    name: str
    value: str


@dataclass
class SesCommonMailHeaders(DataClassJsonMixin):
    """Json object for common mail headers."""

    from_address: List[str] = field(metadata=config(field_name='from'))
    to_address: List[str] = field(metadata=config(field_name='to'))
    messageid: str = field(metadata=config(field_name='messageId'))
    subject: str = ''  # Subject may be missing


@dataclass
class SesMail(DataClassJsonMixin):
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
    headers: List[SesMailHeaders]
    common_headers: SesCommonMailHeaders = field(
        metadata=config(field_name='commonHeaders')
    )
    tags: Dict[str, List[str]]


@dataclass
class SesIndividualRecipient(DataClassJsonMixin):
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


@dataclass
class SesBounce(DataClassJsonMixin):
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
    bounced_recipients: List[SesIndividualRecipient] = field(
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


@dataclass
class SesComplaint(DataClassJsonMixin):
    """
    The JSON object that contains information about a Complaint event.

    * complained_recipients: Recipients that may have submitted the complaint
    * timestamp: The date and time, in ISO8601 format
    * feedbackid: A unique ID for the complaint
    * complaint_sub_type: The subtype of the complaint
    * user_agent: userAgent
    * complaint_feedback_type: This contains the type of feedback
    * arrival_date: The value of the Arrival-Date or Received-Date field

    ``complaint_feedback_type`` will have one of the following:

    * 'abuse': Indicates unsolicited email
    * 'auth-failure': Email authentication failure report
    * 'fraud': Indicates some kind of fraud or phishing activity
    * 'not-spam': Not a spam message
    * 'other': Others not belonging to any category
    * 'virus': A virus is found in the originating message
    """

    complained_recipients: List[SesIndividualRecipient] = field(
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


@dataclass
class SesDelivery(DataClassJsonMixin):
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


@dataclass
class SesSend(DataClassJsonMixin):
    """The JSON object that contains information about a Send event. Has no data."""


@dataclass
class SesReject(DataClassJsonMixin):
    """
    The JSON object that contains information about a Reject event.

    * reason: The reason the email was rejected. The only possible value is Bad content,
        which means that Amazon SES detected that the email contained a virus
    """

    reason: str


@dataclass
class SesOpen(DataClassJsonMixin):
    """
    The JSON object that contains information about a Open event.

    * ip_address: The recipient's IP address
    * timestamp: The date and time when the open event occurred (string)
    * user_agent: The user agent of the device or email client
    """

    ip_address: str = field(metadata=config(field_name='ipAddress'))
    timestamp: str
    user_agent: str = field(metadata=config(field_name='userAgent'))


@dataclass
class SesClick(DataClassJsonMixin):
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


@dataclass
class SesRenderFailure(DataClassJsonMixin):
    """
    The JSON object that contains information about Rendering Failure event.

    * template_name: The name of the template used to send the email
    * error_message: More information about the rendering failure
    """

    template_name: str = field(metadata=config(field_name='templateName'))
    error_message: str = field(metadata=config(field_name='errorMessage'))


@dataclass
class SesDeliveryDelay(DataClassJsonMixin):
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

    delayed_recipients: List[SesIndividualRecipient] = field(
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
    CLICK = 'Click'
    BOUNCE = 'Bounce'
    COMPLAINT = 'Complaint'
    RENDER = 'Rendering Failure'
    DELAY = 'DeliveryDelay'


@dataclass
class SesEvent(DataClassJsonMixin):
    """
    SES Event object JSON which contains the following.

    * event_type: Possible values:
        * 'Delivery'
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
    mail: SesMail
    bounce: Optional[SesBounce] = None
    complaint: Optional[SesComplaint] = None
    delivery: Optional[SesDelivery] = None
    send: Optional[SesSend] = None
    reject: Optional[SesReject] = None
    opened: Optional[SesOpen] = field(metadata=config(field_name='open'), default=None)
    click: Optional[SesClick] = None
    failure: Optional[SesRenderFailure] = None
    delivery_delay: Optional[SesDeliveryDelay] = field(
        metadata=config(field_name='deliveryDelay'), default=None
    )


class SesProcessorAbc(ABC):
    """Abstract Base class for Message Processor."""

    def process(self, ses_event: SesEvent) -> None:
        """
        Process SES Event by calling the appropriate methods.

        :param ses_event: SES Event object
        """
        if ses_event.event_type == SesEvents.BOUNCE.value:
            self.bounce(ses_event)
        elif ses_event.event_type == SesEvents.COMPLAINT.value:
            self.complaint(ses_event)
        elif ses_event.event_type == SesEvents.DELIVERY.value:
            self.delivered(ses_event)
        elif ses_event.event_type == SesEvents.DELAY.value:
            self.delayed(ses_event)
        elif ses_event.event_type == SesEvents.OPEN.value:
            self.opened(ses_event)
        elif ses_event.event_type == SesEvents.CLICK.value:
            self.click(ses_event)

    @abstractmethod
    def bounce(self, ses_event: SesEvent) -> None:
        """Process (Hard) Bounce notifications."""

    @abstractmethod
    def complaint(self, ses_event: SesEvent) -> None:
        """Process Complaint notifications."""

    @abstractmethod
    def delivered(self, ses_event: SesEvent) -> None:
        """Process Delivery notifications."""

    @abstractmethod
    def delayed(self, ses_event: SesEvent) -> None:
        """Process Delivery Delay (Soft Bounce) notifications."""

    @abstractmethod
    def opened(self, ses_event: SesEvent) -> None:
        """Process Open notifications."""

    @abstractmethod
    def click(self, ses_event: SesEvent) -> None:
        """Process Click notifications."""
