"""Support functions for sending an email."""

from email.utils import formataddr, getaddresses, parseaddr
from typing import NamedTuple

from flask import current_app, request
from flask_mailman import EmailMultiAlternatives
from flask_mailman.message import sanitize_address

from html2text import html2text
from premailer import transform

from .. import app, mail
from ..models import EmailAddress, User

__all__ = [
    'EmailAttachment',
    'jsonld_confirm_action',
    'jsonld_view_action',
    'send_email',
]


class EmailAttachment(NamedTuple):
    """An email attachment. Must have content, filename and mimetype."""

    content: str
    filename: str
    mimetype: str


def jsonld_view_action(description, url, title):
    return {
        "@context": "http://schema.org",
        "@type": "EmailMessage",
        "description": description,
        "potentialAction": {"@type": "ViewAction", "name": title, "url": url},
        "publisher": {
            "@type": "Organization",
            "name": current_app.config['SITE_TITLE'],
            "url": request.url_root,
        },
    }


def jsonld_confirm_action(description, url, title):
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


def sanitize_emailaddr(recipient):
    if isinstance(recipient, User):
        formatted = formataddr(recipient.fullname, str(recipient.email))
    elif isinstance(recipient, tuple):
        formatted = formataddr(recipient)
    elif isinstance(recipient, str):
        formatted = recipient
    else:
        raise ValueError(
            "Not a valid email format. Provide either a User object, or"
            " a tuple of (realname, email) or"
            " a preformatted string with Name e.g. '<\"Name\" email>'"
        )

    realname, email_address = parseaddr(formatted)
    if not email_address:
        raise ValueError('No email address to sanitize')

    while True:
        try:
            # try to sanitize the address to check
            sanitize_address((realname, email_address), 'utf-8')
            break
        except ValueError:
            # `realname` is too long, call this function again but
            # truncate realname by 1 character
            realname = realname[:-1]

    # `realname` and `addr` are valid, return formatted string
    return formataddr((realname, email_address))


def send_email(subject, to, content, attachments=None):
    """
    Helper function to send an email.

    :param str subject: Subject line of email message
    :param list to: List of recipients. May contain (a) User objects, (b) tuple of
        (name, email_address), or (c) a pre-formatted email address
    :param str content: HTML content of the message (plain text is auto-generated)
    :param list attachments: List of :class:`EmailAttachment` attachments
    """
    # Parse recipients and convert as needed
    to = [sanitize_emailaddr(recipient) for recipient in to]

    body = html2text(content)
    html = transform(content, base_url=f'https://{app.config["DEFAULT_DOMAIN"]}/')
    msg = EmailMultiAlternatives(
        subject=subject, to=to, body=body, alternatives=[(html, 'text/html')]
    )
    if attachments:
        for attachment in attachments:
            msg.attach(
                content=attachment.content,
                filename=attachment.filename,
                mimetype=attachment.mimetype,
            )
    # If an EmailAddress is blocked, this line will throw an exception
    emails = [EmailAddress.add(email) for name, email in getaddresses(msg.recipients())]
    # FIXME: This won't raise an exception on delivery_state.HARD_FAIL. We need to do
    # catch that, remove the recipient, and notify the user via the upcoming
    # notification centre. (Raise a TransportRecipientError)
    result = mail.send(msg)
    # After sending, mark the address as having received an email
    for ea in emails:
        ea.mark_sent()
    # FIXME: 'result' is a number. Why? We need message-id
    return result
