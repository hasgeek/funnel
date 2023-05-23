"""Support functions for sending an email."""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import formataddr, getaddresses, parseaddr
from typing import Dict, List, Optional, Tuple, Union

from flask import current_app
from flask_mailman import EmailMultiAlternatives
from flask_mailman.message import sanitize_address
from html2text import html2text
from premailer import transform

from baseframe import statsd

from ... import app
from ...models import EmailAddress, EmailAddressBlockedError, User
from ..exc import TransportRecipientError

__all__ = [
    'EmailAttachment',
    'jsonld_confirm_action',
    'jsonld_view_action',
    'process_recipient',
    'send_email',
]

# Email recipient type
EmailRecipient = Union[User, Tuple[Optional[str], str], str]


@dataclass
class EmailAttachment:
    """An email attachment. Must have content, filename and mimetype."""

    content: str
    filename: str
    mimetype: str


def jsonld_view_action(description: str, url: str, title: str) -> Dict[str, object]:
    return {
        "@context": "http://schema.org",
        "@type": "EmailMessage",
        "description": description,
        "potentialAction": {"@type": "ViewAction", "name": title, "url": url},
        "publisher": {
            "@type": "Organization",
            "name": current_app.config['SITE_TITLE'],
            "url": 'https://' + current_app.config['DEFAULT_DOMAIN'] + '/',
        },
    }


def jsonld_confirm_action(description: str, url: str, title: str) -> Dict[str, object]:
    return {
        "@context": "http://schema.org",
        "@type": "EmailMessage",
        "description": description,
        "potentialAction": {
            "@type": "ConfirmAction",
            "name": title,
            "handler": {"@type": "HttpActionHandler", "url": url},
        },
    }


def process_recipient(recipient: EmailRecipient) -> str:
    """
    Process recipient in any of the given input formats.

    These could be:

    1. A User object
    2. A tuple of (name, email)
    3. A pre-formatted string as "Name <email>"

    :param recipient: Recipient of an email
    :returns: RFC 2822 formatted string email address
    """
    if isinstance(recipient, User):
        formatted = formataddr((recipient.fullname, str(recipient.email)))
    elif isinstance(recipient, tuple):
        formatted = formataddr(recipient)
    elif isinstance(recipient, str):
        formatted = recipient
    else:
        raise ValueError(
            "Not a valid email format. Provide either a User object, or a tuple of"
            " (realname, email), or a preformatted string with Name <email>"
        )

    realname, emailaddr = parseaddr(formatted)
    if not emailaddr:
        raise ValueError("No email address to sanitize")

    while True:
        try:
            # try to sanitize the address to check
            sanitize_address((realname, emailaddr), 'utf-8')
            break
        except ValueError:
            # `realname` is too long, call this function again but
            # truncate realname by 1 character
            realname = realname[:-1]

    # `realname` and `emailaddr` are valid, return formatted string
    return formataddr((realname, emailaddr))


def send_email(
    subject: str,
    to: List[EmailRecipient],
    content: str,
    attachments: Optional[List[EmailAttachment]] = None,
    from_email: Optional[EmailRecipient] = None,
    headers: Optional[dict] = None,
) -> str:
    """
    Send an email.

    :param str subject: Subject line of email message
    :param list to: List of recipients. May contain (a) User objects, (b) tuple of
        (name, email_address), or (c) a pre-formatted email address
    :param str content: HTML content of the message (plain text is auto-generated)
    :param list attachments: List of :class:`EmailAttachment` attachments
    :param from_email: Email sender, same format as email recipient
    :param dict headers: Optional extra email headers (for List-Unsubscribe, etc)
    """
    # Parse recipients and convert as needed
    to = [process_recipient(recipient) for recipient in to]
    if from_email:
        from_email = process_recipient(from_email)
    body = html2text(content)
    html = transform(content, base_url=f'https://{app.config["DEFAULT_DOMAIN"]}/')
    msg = EmailMultiAlternatives(
        subject=subject,
        to=to,
        body=body,
        from_email=from_email,
        headers=headers,
        alternatives=[(html, 'text/html')],
    )
    if attachments:
        for attachment in attachments:
            msg.attach(
                content=attachment.content,
                filename=attachment.filename,
                mimetype=attachment.mimetype,
            )
    try:
        # If an EmailAddress is blocked, this line will throw an exception
        emails = [
            EmailAddress.add(email) for name, email in getaddresses(msg.recipients())
        ]
    except EmailAddressBlockedError as exc:
        raise TransportRecipientError(exc) from exc
    # FIXME: This won't raise an exception on delivery_state.HARD_FAIL. We need to do
    # catch that, remove the recipient, and notify the user via the upcoming
    # notification centre. (Raise a TransportRecipientError)

    result = msg.send()

    # After sending, mark the address as having received an email and also update the
    # statistics counters. Note that this will only track emails sent by *this app*.
    # However SES events will track statistics across all apps and hence the difference
    # between this counter and SES event counters will be emails sent by other apps.
    statsd.incr('email_address.sent', count=len(emails))
    for ea in emails:
        ea.mark_sent()

    # FIXME: 'result' is a number. Why? We need message-id
    return str(result)
