from flask import render_template, url_for

from baseframe import _

from .. import signals
from ..transports.email import jsonld_confirm_action, jsonld_view_action, send_email


def send_email_verify_link(useremail):
    """Mail a verification link to the user."""
    subject = _("Verify your email address")
    url = url_for(
        'confirm_email',
        _external=True,
        email_hash=useremail.email_address.email_hash,
        secret=useremail.verification_code,
        utm_medium='email',
        utm_campaign='verify',
    )
    jsonld = jsonld_confirm_action(subject, url, _("Verify email address"))
    content = render_template(
        'email_account_verify.html.jinja2',
        fullname=useremail.user.fullname,
        url=url,
        jsonld=jsonld,
    )
    send_email(subject, [(useremail.user.fullname, useremail.email)], content)


def send_password_reset_link(email, user, token):
    """Mail a password reset link to the user"""
    subject = _("Reset your password")
    url = url_for(
        'reset_email',
        _external=True,
        token=token,
        utm_medium='email',
        utm_campaign='reset',
    )
    jsonld = jsonld_view_action(subject, url, _("Reset password"))
    content = render_template(
        'email_account_reset.html.jinja2',
        fullname=user.fullname,
        url=url,
        jsonld=jsonld,
    )
    send_email(subject, [(user.fullname, email)], content)


@signals.project_crew_membership_added.connect
def send_email_for_project_crew_membership_added(
    sender, project, membership, actor, user
):
    send_email(
        subject=_("You have been added to {project} as a crew member").format(
            project=project.title
        ),
        to=[user],
        content=render_template(
            'email_project_crew_membership_add_notification.html.jinja2',
            actor=actor,
            project=project,
            membership=membership,
        ),
    )


@signals.project_crew_membership_invited.connect
def send_email_for_project_crew_membership_invited(
    sender, project, membership, actor, user
):
    send_email(
        subject=_("You have been invited to {project} as a crew member").format(
            project=project.title
        ),
        to=[user],
        content=render_template(
            'email_project_crew_membership_invite_notification.html.jinja2',
            actor=actor,
            project=project,
            membership=membership,
        ),
    )


@signals.project_crew_membership_revoked.connect
def send_email_for_project_crew_membership_revoked(
    sender, project, membership, actor, user
):
    send_email(
        subject=_("You have been removed from {project} as a crew member").format(
            project=project.title
        ),
        to=[user],
        content=render_template(
            'email_project_crew_membership_revoke_notification.html.jinja2',
            actor=actor,
            project=project,
            membership=membership,
        ),
    )
