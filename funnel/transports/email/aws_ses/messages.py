from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from dataclasses_json import config, dataclass_json

__all__ = ['Bounce', 'Complaint', 'Delivery', 'DeliveryDelay', 'Processor', 'SesEvent']


@dataclass_json
@dataclass
class MailHeaders:
    """ Mail Headers have name/value pairs """

    name: str
    value: str


@dataclass_json
@dataclass
class CommonMailHeaders:
    """ Json Object for Common Mail Headers """

    from_address: List[str] = field(metadata=config(field_name="from"))
    to_address: List[str] = field(metadata=config(field_name="to"))
    subject: str
    message_id: str = field(metadata=config(field_name="messageId"))


@dataclass_json
@dataclass
class Mail:
    """
    The JSON object that contains information about a mail object

    timestamp:  The date and time, in ISO8601 format

    messageId:  A unique ID that Amazon SES assigned to the message.

    source:     The email address that the message was sent from

    sourceArn: The Amazon Resource Name (ARN) of the identity that was used

    sendingAccountId: The AWS account ID of the account

    destination: A list of email addresses that were recipients of the original mail.

    headersTruncated: Are headers Truncated?

    headers: A list of the email's original headers.

    commonHeaders: A list of the email's original, commonly used headers.
    """

    timestamp: str
    message_id: str = field(metadata=config(field_name="messageId"))
    source: str
    source_arn: str = field(metadata=config(field_name="sourceArn"))
    sending_account_id: str = field(metadata=config(field_name="sendingAccountId"))
    destination: List[str]
    headers: List[MailHeaders]
    common_headers: CommonMailHeaders = field(
        metadata=config(field_name="commonHeaders")
    )
    tags: Dict[str, List[str]]


@dataclass_json
@dataclass
class BouncedRecipients:
    """
    Recipients for whom the Email bounced.

        emailAddress(str):      Email Address

        action(str):            Action (Mostly "failed")

        status(str):            Numeric Status in String format.

        diagnosticCode(str):    SMTP Diagnostic Code

    """

    email_address: str = field(metadata=config(field_name="emailAddress"))
    action: Optional[str] = None
    status: Optional[str] = None
    diagnostic_code: Optional[str] = field(
        metadata=config(field_name="diagnosticCode"), default=None
    )


@dataclass_json
@dataclass
class Bounce:
    """
    The JSON object that contains information about a Bounce event.

        bounceType: The type of bounce

        bounceSubType: The subtype of the bounce

        bouncedRecipients: List of Recipients for whom the Email Bounced

        timestamp: The date and time, in ISO8601 format

        feedbackId(str): A unique ID for the bounce.

        reportingMTA(str): The value of the Reporting-MTA field from the DSN.
                           This is the value of the Message Transfer Authority (MTA)
                           that attempted to perform the delivery, relay, or
                           gateway operation described in the DSN.
    """

    bounce_type: str = field(metadata=config(field_name="bounceType"))
    bounce_sub_type: str = field(metadata=config(field_name="bounceSubType"))
    bounced_recipients: List[BouncedRecipients] = field(
        metadata=config(field_name="bouncedRecipients")
    )
    timestamp: str
    feedback_id: str = field(metadata=config(field_name="feedbackId"))
    reporting_mta: Optional[str] = field(
        metadata=config(field_name="reportingMTA"), default=None
    )

    def is_hard_bounce(self) -> bool:
        """
        Check if Bounce message is a hard bounce.
        If you receive this type of bounce, you should remove the
        recipient's email address from your mailing list.
        :return: True if it is hard bounce, false if not.
        """
        return self.bounce_type == "Permanent"


@dataclass_json
@dataclass
class Complaint:
    """
    The JSON object that contains information about a Complaint event

        complainedRecipients: Recipients that may have submitted the complaint.

        timestamp: The date and time, in ISO8601 format

        feedbackId: A unique ID for the complaint.

        complaintSubType: The subtype of the complaint

        userAgent: userAgent

        complaintFeedbackType: This contains the type of feedback.

        arrivalDate: The value of the Arrival-Date or Received-Date field

    complaintFeedbackType will have one of the following:

        abuse:          Indicates unsolicited email

        auth-failure:   Email authentication failure report.

        fraud:          Indicates some kind of fraud or phishing activity.

        not-spam:       Not a Spam

        other:          Others not belonging to any category

        virus:          A virus is found in the originating message.
    """

    complained_recipients: List[BouncedRecipients] = field(
        metadata=config(field_name="complainedRecipients")
    )
    timestamp: str
    feedback_id: str = field(metadata=config(field_name="feedbackId"))
    complaint_sub_type: Optional[str] = field(
        metadata=config(field_name="complaintSubType"), default=None
    )
    user_agent: Optional[str] = field(
        metadata=config(field_name="userAgent"), default=None
    )
    complaint_feedback_type: Optional[str] = field(
        metadata=config(field_name="complaintFeedbackType"), default=None
    )
    arrival_date: Optional[str] = field(
        metadata=config(field_name="arrivalDate"), default=None
    )


@dataclass_json
@dataclass
class Delivery:
    """
    The JSON object that contains information about a Delivery event

        timestamp:            The date and time.

        processingTimeMillis: Time to process and send the Message.

        recipients:           A list of intended recipients.

        smtpResponse:         The SMTP response.

        reportingMTA:         Host name of the Amazon SES mail server.
    """

    timestamp: str
    processing_time: int = field(metadata=config(field_name="processingTimeMillis"))
    recipients: List[str]
    smtp_response: str = field(metadata=config(field_name="smtpResponse"))
    reporting_mta: str = field(metadata=config(field_name="reportingMTA"))


class Send:
    """ The JSON object that contains information about a send event. """


@dataclass_json
@dataclass
class Reject:
    """
    The JSON object that contains information about a Reject event

        reason: The reason the email was rejected. The only possible value
                is Bad content, which means that Amazon SES detected that the
                email contained a virus

    """

    reason: str


@dataclass_json
@dataclass
class Open:
    """
    The JSON object that contains information about a Open event

        ipAddress:       The recipient's IP address.

        timestamp:       The date and time when the open event occurred

        userAgent:       The user agent of the device or email client
    """

    ip_address: str = field(metadata=config(field_name="ipAddress"))
    timestamp: str
    user_agent: str = field(metadata=config(field_name="userAgent"))


@dataclass_json
@dataclass
class Click:
    """
    The JSON object that contains information about a Click event

    ipAddress:        The recipient's IP address.

    timestamp:        The date and time when the click event occurred

    userAgent:        The user agent of the client that the recipient

    link:             The URL of the link that the recipient clicked.

    linkTags:         A list of tags that were added to the link.
    """

    ip_address: str = field(metadata=config(field_name="ipAddress"))
    timestamp: str
    user_agent: str = field(metadata=config(field_name="userAgent"))
    link: str
    link_tags: Optional[Dict[str, List[str]]] = field(
        metadata=config(field_name="linkTags"), default=None
    )


@dataclass_json
@dataclass
class RenderFailure:
    """
    The JSON object that contains information about Rendering Failure event

    templateName:  The name of the template used to send the email.

    errorMessage:  More information about the rendering failure.
    """

    template_name: str = field(metadata=config(field_name="templateName"))
    error_message: str = field(metadata=config(field_name="errorMessage"))


@dataclass_json
@dataclass
class DeliveryDelay:
    """
    The JSON object that contains information about a DeliveryDelay event.

    delayedRecipients:  Information about the recipient of the email.

    expirationTime:     When Amazon SES will stop trying to deliver the message.

    reportingMTA:       The IP address of the Message Transfer Agent (MTA)

    timestamp:          The date and time when the delay occurred

    delayType:          The type of delay. Possible values are:

     InternalFailure – An internal Amazon SES issue caused the message to be delayed.

     General – A generic failure occurred during the SMTP conversation.

     MailboxFull – The recipient's mailbox is full.

     SpamDetected – The recipient's mail server has detected a large amount of SPAM.

     RecipientServerError – A temporary issue with the recipient's email server.

     IPFailure – IP address that's sending the message is being blocked or throttled.

     TransientCommunicationGeneral – Temporary communication failure.

     Undetermined – Amazon SES wasn't able to determine the reason.
    """

    delayed_recipients: List[BouncedRecipients] = field(
        metadata=config(field_name="delayedRecipients")
    )
    expiration_time: str = field(metadata=config(field_name="expirationTime"))
    reporting_mta: str = field(metadata=config(field_name="reportingMTA"))
    timestamp: str
    delay_type: str = field(metadata=config(field_name="delayType"))


class SesEvents(Enum):
    """
    Types of SesEvents
    """

    DELIVERY = "Delivery"
    SEND = "Send"
    REJECT = "Reject"
    OPEN = "Open"
    Click = "Click"
    BOUNCE = "Bounce"
    COMPLAINT = "Complaint"
    RENDER = "Rendering Failure"
    DELAY = "DeliveryDelay"


@dataclass_json
@dataclass
class SesEvent:
    """
    SES Event object JSON which contains the following:
    eventType: Possible values: Delivery, Send, Reject, Open, Click, Bounce,
                                Complaint, Rendering Failure, or DeliveryDelay.

    mail :     A JSON object that contains information about the email

    bounce:    This field is only present if eventType is Bounce.

    complaint: This field is only present if eventType is Complaint.

    delivery:  This field is only present if eventType is Delivery.

    send:      This field is only present if eventType is Send.

    reject:    This field is only present if eventType is Reject.

    open:      This field is only present if eventType is Open.

    click:     This field is only present if eventType is Click.

    failure:   This field is only present if eventType is Rendering Failure.

    deliveryDelay:  This field is only present if eventType is DeliveryDelay.
    """

    event_type: str = field(metadata=config(field_name="eventType"))
    mail: Mail
    bounce: Optional[Bounce] = None
    complaint: Optional[Complaint] = None
    delivery: Optional[Delivery] = None
    send: Optional[Send] = None
    reject: Optional[Reject] = None
    opened: Optional[Open] = field(metadata=config(field_name="open"), default=None)
    click: Optional[Click] = None
    failure: Optional[RenderFailure] = None
    delivery_delay: Optional[DeliveryDelay] = field(
        metadata=config(field_name="deliveryDelay"), default=None
    )


class Processor(ABC):
    """
    Abstract Base class for Message Processor.
    """

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
