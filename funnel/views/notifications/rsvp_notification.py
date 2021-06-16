from flask import render_template
from flask_babelhg import get_locale

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
    emoji_prefix = "🎟️ "

    def email_attachments(self):
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
                    content=schedule_ical(self.rsvp.project, self.rsvp),
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

    rsvp: Rsvp
    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you have registered for this project")

    datetime_format = "EEE, dd MMM yyyy, hh:mm a"
    datetime_format_sms = "EEE, dd MMM, hh:mm a"

    def web(self):
        return render_template('notifications/rsvp_yes_web.html.jinja2', view=self)

    def email_subject(self):
        return self.emoji_prefix + _("Registration confirmation for {project}").format(
            project=self.rsvp.project.joined_title()
        )

    def email_content(self):
        return render_template(
            'notifications/rsvp_yes_email.html.jinja2',
            view=self,
            jsonld=email.jsonld_view_action(
                self.rsvp.project.joined_title(),
                self.rsvp.project.url_for(_external=True),
                _("View project"),
            ),
        )

    def sms(self) -> OneLineTemplate:
        project = self.rsvp.project
        next_at = project.next_starting_at()
        if next_at:
            template = _(
                "You have registered for {project}."
                " The next session starts {datetime}."
                " You will get a reminder 10m prior."
            )
        else:
            template = _("You have registered for {project}")
        return OneLineTemplate(
            text1=template.format(
                project=project.joined_title('>'),
                datetime=datetime_filter(
                    next_at, self.datetime_format_sms, locale=get_locale()
                ),
            ),
            url=shortlink(project.url_for(_external=True, **self.tracking_tags('sms'))),
        )


@RegistrationCancellationNotification.renderer
class RenderRegistrationCancellationNotification(RegistrationBase, RenderNotification):
    """Notify the participant when they cancel registration."""

    rsvp: Rsvp
    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you had registered for this project")

    def web(self):
        return render_template('notifications/rsvp_no_web.html.jinja2', view=self)

    def email_subject(self):
        return self.emoji_prefix + _("Registration cancelled for {project}").format(
            project=self.rsvp.project.joined_title()
        )

    def email_content(self):
        return render_template(
            'notifications/rsvp_no_email.html.jinja2',
            view=self,
            jsonld=email.jsonld_view_action(
                self.rsvp.project.joined_title(),
                self.rsvp.project.url_for(_external=True),
                _("View project"),
            ),
        )

    def sms(self) -> MessageTemplate:
        return MessageTemplate(
            message=_("You have cancelled your registration for {project}").format(
                project=self.rsvp.project.joined_title('>'),
            ),
        )
