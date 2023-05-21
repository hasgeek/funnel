"""View helper functions for sending email inline in a request."""

from __future__ import annotations

from flask import render_template, url_for

from baseframe import _

from ..models import Account, AccountEmailClaim
from ..transports.email import jsonld_confirm_action, jsonld_view_action, send_email


def send_email_verify_link(emailclaim: AccountEmailClaim) -> str:
    """Mail a verification link to the user."""
    subject = _("Verify your email address")
    url = url_for(
        'confirm_email',
        _external=True,
        email_hash=emailclaim.email_address.email_hash,
        secret=emailclaim.verification_code,
        utm_medium='email',
        utm_source='account-verify',
    )
    jsonld = jsonld_confirm_action(subject, url, _("Verify email address"))
    content = render_template(
        'email_account_verify.html.jinja2',
        fullname=emailclaim.account.title,
        url=url,
        jsonld=jsonld,
    )
    return send_email(subject, [(emailclaim.account.title, emailclaim.email)], content)


def send_password_reset_link(email: str, user: Account, otp: str, token: str) -> str:
    """Mail a password reset OTP and link to the user."""
    subject = _("Reset your password - OTP {otp}").format(otp=otp)
    url = url_for(
        'reset_with_token',
        _external=True,
        token=token,
        utm_medium='email',
        utm_source='account-reset',
    )
    jsonld = jsonld_view_action(subject, url, _("Reset password"))
    content = render_template(
        'email_account_reset.html.jinja2',
        fullname=user.title,
        url=url,
        jsonld=jsonld,
        otp=otp,
    )
    return send_email(subject, [(user.fullname, email)], content)
