from email.utils import formataddr, getaddresses

from flask import current_app, render_template, request, url_for
from flask_mailman import EmailMultiAlternatives

from html2text import html2text
from premailer import transform

from baseframe import _

from .. import mail
from ..models import EmailAddress, User


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


def send_email(subject, to, content):
    """Helper function to send an email"""
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
    html = transform(content, base_url=request.url_root)
    msg = EmailMultiAlternatives(
        subject=subject, to=to, body=body, alternatives=[(html, 'text/html')]
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


def send_email_verify_link(useremail):
    """Mail a verification link to the user."""
    subject = _("Verify your email address")
    url = url_for(
        'confirm_email',
        _external=True,
        email_hash=useremail.email_address.email_hash,
        secret=useremail.verification_code,
    )
    jsonld = jsonld_confirm_action(subject, url, _("Verify email address"))
    content = render_template(
        'email_account_verify.html.jinja2',
        fullname=useremail.user.fullname,
        url=url,
        jsonld=jsonld,
    )
    send_email(subject, [(useremail.user.fullname, useremail.email)], content)


def send_password_reset_link(email, user, secret):
    """Mail a password reset link to the user"""
    subject = _("Reset your password")
    url = url_for('reset_email', _external=True, buid=user.buid, secret=secret)
    jsonld = jsonld_view_action(subject, url, _("Reset password"))
    content = render_template(
        'email_account_reset.html.jinja2',
        fullname=user.fullname,
        url=url,
        jsonld=jsonld,
    )
    send_email(subject, [(user.fullname, email)], content)
