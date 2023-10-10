"""Support functions for sending an email."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.utils import formataddr, getaddresses, make_msgid, parseaddr
from typing import Optional, Union

from flask import current_app
from flask_mailman import EmailMultiAlternatives
from flask_mailman.message import sanitize_address
from html2text import html2text
from premailer import transform
from werkzeug.datastructures import Headers

from baseframe import _, statsd

from ... import app
from ...models import Account, EmailAddress, EmailAddressBlockedError, Rsvp
from ..exc import TransportRecipientError

__all__ = [
    'EmailAttachment',
    'jsonld_confirm_action',
    'jsonld_event_reservation',
    'jsonld_view_action',
    'process_recipient',
    'send_email',
]

# Email recipient type
EmailRecipient = Union[Account, tuple[Optional[str], str], str]


@dataclass
class EmailAttachment:
    """An email attachment. Must have content, filename and mimetype."""

    content: str
    filename: str
    mimetype: str


def jsonld_view_action(description: str, url: str, title: str) -> dict[str, object]:
    """Schema.org JSON-LD markup for an email view action."""
    return {
        '@context': 'https://schema.org',
        '@type': 'EmailMessage',
        'description': description,
        'potentialAction': {'@type': 'ViewAction', 'name': title, 'url': url},
        'publisher': {
            '@type': 'Organization',
            'name': current_app.config['SITE_TITLE'],
            'url': 'https://' + current_app.config['DEFAULT_DOMAIN'] + '/',
        },
    }


def jsonld_confirm_action(description: str, url: str, title: str) -> dict[str, object]:
    """Schema.org JSON-LD markup for an email confirmation action."""
    return {
        '@context': 'https://schema.org',
        '@type': 'EmailMessage',
        'description': description,
        'potentialAction': {
            '@type': 'ConfirmAction',
            'name': title,
            'handler': {'@type': 'HttpActionHandler', 'url': url},
        },
    }


def jsonld_event_reservation(rsvp: Rsvp) -> dict[str, object]:
    """Schema.org JSON-LD markup for an event reservation."""
    location: str | dict[str, object]
    venue = rsvp.project.primary_venue
    if venue is not None:
        location = {
            '@type': 'Place',
            'name': venue.title,
        }
        if venue.address1:
            postal_address = {
                '@type': 'PostalAddress',
                'streetAddress': venue.address1,
                'addressLocality': venue.city,
                'addressRegion': venue.state,
                'postalCode': venue.postcode,
                'addressCountry': venue.country,
            }
            location['address'] = postal_address
    else:
        location = rsvp.project.location
    return {
        '@context': 'https://schema.org',
        '@type': 'EventReservation',
        'reservationNumber': rsvp.uuid_b58,
        'reservationStatus': (
            'https://schema.org/ReservationConfirmed'
            if rsvp.state.YES
            else 'https://schema.org/ReservationCancelled'
            if rsvp.state.NO
            else 'https://schema.org/ReservationPending'
        ),
        'underName': {
            '@type': 'Person',
            'name': rsvp.participant.fullname,
        },
        'reservationFor': {
            '@type': 'Event',
            'name': rsvp.project.joined_title,
            'url': rsvp.project.absolute_url,
            'startDate': rsvp.project.start_at,
            'location': location,
            'performer': {
                '@type': 'Organization',
                'name': rsvp.project.account.title,
            },
        },
        'numSeats': '1',
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
    if isinstance(recipient, Account):
        formatted = formataddr((recipient.title, str(recipient.email)))
    elif isinstance(recipient, tuple):
        formatted = formataddr(recipient)
    elif isinstance(recipient, str):
        formatted = recipient
    else:
        raise ValueError(
            "Not a valid email format. Provide either an Account object, or a tuple of"
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
    to: list[EmailRecipient],
    content: str,
    attachments: list[EmailAttachment] | None = None,
    from_email: EmailRecipient | None = None,
    headers: dict | Headers | None = None,
    base_url: str | None = None,
) -> str:
    """
    Send an email.

    :param subject: Subject line of email message
    :param to: List of recipients. May contain (a) Account objects, (b) tuple of
        (name, email_address), or (c) a pre-formatted email address
    :param content: HTML content of the message (plain text is auto-generated)
    :param attachments: List of :class:`EmailAttachment` attachments
    :param from_email: Email sender, same format as email recipient
    :param headers: Optional extra email headers (for List-Unsubscribe, etc)
    :param base_url: Optional base URL for all relative links in the email
    """
    # Parse recipients and convert as needed
    to = [process_recipient(recipient) for recipient in to]
    if from_email:
        from_email = process_recipient(from_email)
    body = html2text(content)
    html = transform(
        content, base_url=base_url or f'https://{app.config["DEFAULT_DOMAIN"]}/'
    )
    headers = Headers() if headers is None else Headers(headers)

    # Amazon SES will replace Message-ID, so we keep our original in an X- header
    headers['Message-ID'] = headers['X-Original-Message-ID'] = make_msgid(
        domain=current_app.config['DEFAULT_DOMAIN']
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        to=to,
        body=body,
        from_email=from_email,
        headers=dict(headers),  # Flask-Mailman<=0.3.0 will trip on a Headers object
        alternatives=[(html, 'text/html')],
    )
    if attachments:
        for attachment in attachments:
            msg.attach(
                content=attachment.content,
                filename=attachment.filename,
                mimetype=attachment.mimetype,
            )

    email_addresses: list[EmailAddress] = []
    for _name, email in getaddresses(msg.recipients()):
        try:
            # If an EmailAddress is blocked, this line will throw an exception
            ea = EmailAddress.add(email)
            # If an email address is hard-bouncing, it cannot be emailed or it'll hurt
            # sender reputation. There is no automated way to flag an email address as
            # no longer bouncing, so it'll require customer support intervention
            if ea.delivery_state.HARD_FAIL:
                statsd.incr('email_address.send_hard_fail')
                raise TransportRecipientError(
                    _(
                        "This email address is bouncing messages: {email}. If you"
                        " believe this to be incorrect, please contact customer support"
                    ).format(email=email)
                )
            email_addresses.append(ea)
        except EmailAddressBlockedError as exc:
            statsd.incr('email_address.send_blocked')
            raise TransportRecipientError(
                _("This email address has been blocked: {email}").format(email=email)
            ) from exc

    try:
        msg.send()
    except smtplib.SMTPRecipientsRefused as exc:
        if len(exc.recipients) == 1:
            if len(to) == 1:
                message = _("This email address is not valid")
            else:
                message = _("This email address is not valid: {email}").format(
                    email=list(exc.recipients.keys())[0]
                )
        else:
            if len(to) == len(exc.recipients):
                # We don't know which recipients were rejected, so the error message
                # can't identify them
                message = _("These email addresses are not valid")
            else:
                message = _("These email addresses are not valid: {emails}").format(
                    emails=_(", ").join(exc.recipients.keys())
                )
            statsd.incr('email_address.send_smtp_refused')
        raise TransportRecipientError(message) from exc

    # After sending, mark the address as having received an email and also update the
    # statistics counters. Note that this will only track emails sent by *this app*.
    # However SES events will track statistics across all apps and hence the difference
    # between this counter and SES event counters will be emails sent by other apps.
    statsd.incr('email_address.sent', count=len(email_addresses))
    for ea in email_addresses:
        ea.mark_sent()

    return headers['Message-ID']
