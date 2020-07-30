from collections import namedtuple
from email.utils import formataddr, getaddresses

from flask import current_app, render_template, request, url_for
from flask_mailman import EmailMultiAlternatives

from flask_babelhg import force_locale, get_locale
from html2text import html2text
from premailer import transform

from baseframe import _

from .. import app, mail, rq, signals
from ..models import EmailAddress, Project, User
from .schedule import schedule_ical

EmailAttachment = namedtuple('EmailAttachment', ['content', 'filename', 'mimetype'])


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


@signals.organization_admin_membership_added.connect
def send_email_for_organization_admin_membership_added(
    sender, organization, membership, actor, user
):
    send_email(
        subject=_("You have been added to {organization} as an admin").format(
            organization=organization.title
        ),
        to=[user],
        content=render_template(
            'email_organization_admin_membership_add_notification.html.jinja2',
            actor=actor,
            organization=organization,
            membership=membership,
        ),
    )


@signals.organization_admin_membership_revoked.connect
def send_email_for_organization_admin_membership_revoked(
    sender, organization, membership, actor, user
):
    send_email(
        subject=_("You have been removed from {organization} as an admin").format(
            organization=organization.title
        ),
        to=[user],
        content=render_template(
            'email_organization_admin_membership_revoke_notification.html.jinja2',
            actor=actor,
            organization=organization,
            membership=membership,
        ),
    )


@signals.user_registered_for_project.connect
def send_email_for_project_registration(project, user):
    background_project_registration_email.queue(
        project_id=project.id, user_id=user.id, locale=get_locale()
    )


@signals.user_cancelled_project_registration.connect
def send_email_for_project_deregistration(project, user):
    send_email(
        subject=_("Registration cancelled for {project}").format(
            project=project.title
        ),
        to=[user],
        content=render_template(
            'email_project_deregister.html.jinja2', user=user, project=project,
        ),
    )


@rq.job('funnel')
def background_project_registration_email(project_id, user_id, locale):
    with app.app_context(), force_locale(locale):
        project = Project.query.get(project_id)
        user = User.query.get(user_id)
        send_email(
            subject=_("Registration confirmation for {project}").format(
                project=project.title
            ),
            to=[user],
            attachments=[
                EmailAttachment(
                    content=schedule_ical(project),
                    filename='%s.ics' % project.name,
                    mimetype='text/calendar',
                )
            ],
            content=render_template(
                'email_project_registration.html.jinja2', user=user, project=project,
            ),
        )


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
