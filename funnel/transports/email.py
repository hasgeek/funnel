"""
Support functions for sending an email.
"""

from email.utils import formataddr, getaddresses
from typing import NamedTuple

from flask import current_app, request
from flask_mailman import EmailMultiAlternatives

from html2text import html2text
from premailer import transform

from .. import app, mail
from ..models import EmailAddress, User

__all__ = ['EmailAddress', 'send_email']


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
    to = [
        # Is the recipient a User object? Send to "{user.fullname} <{user.email}>"
        formataddr((recipient.fullname, str(recipient.email)))
        if isinstance(recipient, User)
        # Is the recipient (name, email)? Reformat to "{name} <{email}>"
        else formataddr(recipient) if isinstance(recipient, tuple)
        # Neither? Pass it in as is
        else recipient
        for recipient in to
    ]
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
    # TODO: This won't raise an exception on delivery_state.HARD_FAIL. We need to do
    # catch that, remove the recipient, and notify the user via the upcoming
    # notification centre.
    result = mail.send(msg)
    # After sending, mark the address as having received an email
    for ea in emails:
        ea.mark_sent()
    return result
