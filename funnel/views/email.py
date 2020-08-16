from flask import render_template, url_for

from flask_babelhg import force_locale, get_locale

from baseframe import _

from .. import app, rq, signals
from ..models import Project, User
from ..transports.email import (
    EmailAttachment,
    jsonld_confirm_action,
    jsonld_view_action,
    send_email,
)
from .schedule import schedule_ical


def send_email_verify_link(useremail):
    """Mail a verification link to the user."""
    subject = _("Verify your email address")
    url = url_for(
        'confirm_email',
        _external=True,
        email_hash=useremail.email_address.email_hash,
        secret=useremail.verification_code,
        utm_medium='email',
        utm_campaign='website',
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
        utm_campaign='website',
    )
    jsonld = jsonld_view_action(subject, url, _("Reset password"))
    content = render_template(
        'email_account_reset.html.jinja2',
        fullname=user.fullname,
        url=url,
        jsonld=jsonld,
    )
    send_email(subject, [(user.fullname, email)], content)


@signals.proposal_submitted.connect
def send_email_for_proposal_submission(proposal):
    for membership in proposal.project.active_editor_memberships:
        if membership.user.email:
            send_email(
                subject=_("New proposal in {project}").format(
                    project=proposal.project.title
                ),
                to=[membership.user],
                content=render_template(
                    'email_new_proposal_submission.html.jinja2',
                    proposal=proposal,
                    project=proposal.project,
                    editor=membership.user,
                ),
            )


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
def send_email_for_project_registration(rsvp, project, user):
    if user.email:
        background_project_registration_email.queue(
            project_id=project.id, user_id=user.id, locale=get_locale()
        )


@signals.user_cancelled_project_registration.connect
def send_email_for_project_deregistration(rsvp, project, user):
    if user.email:
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
