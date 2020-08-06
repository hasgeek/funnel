from dataclasses import dataclass, field
from typing import List, Optional, Dict

from dataclasses_json import dataclass_json, config


@dataclass_json
@dataclass
class MailHeaders:
    """
    Mail Headers have name/value pairs
    """
    name: str
    value: str


@dataclass_json
@dataclass
class CommonMailHeaders:
    """
    Json Object for Common Mail Headers
    """
    from_address: List[str] = field(metadata=config(field_name="from"))
    to_address: List[str] = field(metadata=config(field_name="to"))
    subject: str
    messageId: str


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
    messageId: str
    source: str
    sourceArn: str
    sendingAccountId: str
    destination: List[str]
    headers: List[MailHeaders]
    commonHeaders: CommonMailHeaders
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
    emailAddress: str
    action: Optional[str] = None
    status: Optional[str] = None
    diagnosticCode: Optional[str] = None


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
    bounceType: str
    bounceSubType: str
    bouncedRecipients: List[BouncedRecipients]
    timestamp: str
    feedbackId: str
    reportingMTA: Optional[str] = None

    def is_hard_bounce(self) -> bool:
        """
        Check if Bounce message is a hard bounce.
        If you receive this type of bounce, you should remove the
        recipient's email address from your mailing list.
        :return: True if it is hard bounce, false if not.
        """
        return self.bounceType == "Permanent"


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
    complainedRecipients: List[BouncedRecipients]
    timestamp: str
    feedbackId: str
    complaintSubType: str
    userAgent: Optional[str] = None
    complaintFeedbackType: Optional[str] = None
    arrivalDate: Optional[str] = None


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
    processingTimeMillis: int
    recipients: List[str]
    smtpResponse: str
    reportingMTA: str


class Send:
    """
    The JSON object that contains information about a send event is always empty.
    """
    pass


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
    ipAddress: str
    timestamp: str
    userAgent: str


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
    ipAddress: str
    timestamp: str
    userAgent: str
    link: str
    linkTags: Optional[Dict[str, List[str]]] = None


@dataclass_json
@dataclass
class RenderFailure:
    """
    The JSON object that contains information about Rendering Failure event

    templateName:  The name of the template used to send the email.

    errorMessage:  More information about the rendering failure.
    """
    templateName: str
    errorMessage: str


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
    delayedRecipients: List[BouncedRecipients]
    expirationTime: str
    reportingMTA: str
    timestamp: str
    delayType: str


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
    eventType: str
    mail: Mail
    bounce: Optional[Bounce] = None
    complaint: Optional[Complaint] = None
    delivery: Optional[Delivery] = None
    send: Optional[Send] = None
    reject: Optional[Reject] = None
    open: Optional[Open] = None
    click: Optional[Click] = None
    failure: Optional[RenderFailure] = None
    deliveryDelay: Optional[DeliveryDelay] = None
