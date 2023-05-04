"""Project registration (RSVP) notifications."""

from __future__ import annotations

from typing import List, Optional

from flask import render_template
from flask_babel import get_locale

from baseframe import _, __
from baseframe.filters import datetime_filter

from ...models import (
    RegistrationCancellationNotification,
    RegistrationConfirmationNotification,
    Rsvp,
)
from ...transports import email
from ...transports.sms import MessageTemplate, OneLineTemplate
from ..helpers import shortlink
from ..notification import RenderNotification
from ..schedule import schedule_ical


class RegistrationBase:
    """Base class for project registration notifications."""

    rsvp: Rsvp
    emoji_prefix = "🎟️ "

    def email_attachments(self) -> Optional[List[email.EmailAttachment]]:
        """Provide a calendar attachment."""
        # Attach a vCalendar of schedule, but only if there are sessions.
        # This will include the user as an attendee with RSVP=TRUE/FALSE.
        # The mimetype apparently changes how Gmail interprets the file. text/calendar
        # works for a single session and shows the date, while application/ics shows all
        # sessions without a single prominent date. Behaviour in other mail clients is
        # untested at this time.
        if self.rsvp.project.start_at:
            # Session count will be 0 when there are no scheduled sessions, but the
            # Project has an independent `start_at`. If 0 or 1, treat as one session
            session_count = self.rsvp.project.session_count
            return [
                email.EmailAttachment(
                    content=schedule_ical(
                        self.rsvp.project, self.rsvp, future_only=True
                    ),
                    filename='event.ics',
                    mimetype=(
                        'text/calendar'
                        if session_count in (0, 1)
                        else 'application/ics'
                    ),
                )
            ]
        return None


@RegistrationConfirmationNotification.renderer
class RenderRegistrationConfirmationNotification(RegistrationBase, RenderNotification):
    """Notify the participant when they register."""

    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you have registered for this project")
    hero_image = "https://images.hasgeek.com/embed/file/19acf7182396436781d3653a0914a2cf?size=196x138"
    email_title = "Registration confirmed!"

    datetime_format = "EEE, dd MMM yyyy, hh:mm a"
    datetime_format_sms = "EEE, dd MMM, hh:mm a"

    def web(self):
        return render_template('notifications/rsvp_yes_web.html.jinja2', view=self)

    def email_subject(self):
        return self.emoji_prefix + _("Registration confirmation for {project}").format(
            project=self.rsvp.project.joined_title
        )

    def email_content(self):
        return render_template(
            'notifications/rsvp_yes_email.html.jinja2',
            view=self,
            jsonld=email.jsonld_view_action(
                self.rsvp.project.joined_title,
                self.rsvp.project.url_for(_external=True),
                _("View project"),
            ),
        )

    def sms(self) -> OneLineTemplate:
        project = self.rsvp.project
        next_at = project.next_starting_at()
        if next_at:
            template = _("You have registered for {project}. Next session: {datetime}.")
        else:
            template = _("You have registered for {project}")
        return OneLineTemplate(
            text1=template.format(
                project=project.joined_title,
                datetime=datetime_filter(
                    next_at, self.datetime_format_sms, locale=get_locale()
                ),
            ),
            url=shortlink(
                project.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )


@RegistrationCancellationNotification.renderer
class RenderRegistrationCancellationNotification(RegistrationBase, RenderNotification):
    """Notify the participant when they cancel registration."""

    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you had registered for this project")
    hero_image = "https://images.hasgeek.com/embed/file/9e785b5461b54e389c442d77c2abff71?size=196x134"
    email_title = "Registration cancelled"

    def web(self):
        return render_template('notifications/rsvp_no_web.html.jinja2', view=self)

    def email_subject(self):
        return self.emoji_prefix + _("Registration cancelled for {project}").format(
            project=self.rsvp.project.joined_title
        )

    def email_content(self):
        return render_template(
            'notifications/rsvp_no_email.html.jinja2',
            view=self,
            jsonld=email.jsonld_view_action(
                self.rsvp.project.joined_title,
                self.rsvp.project.url_for(_external=True),
                _("View project"),
            ),
        )

    def sms(self) -> MessageTemplate:
        return MessageTemplate(
            message=_("You have cancelled your registration for {project}").format(
                project=self.rsvp.project.joined_title,
            ),
        )
