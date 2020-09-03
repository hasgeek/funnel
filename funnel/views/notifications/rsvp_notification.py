from flask import render_template

from baseframe import _, __

from ...models import (
    RegistrationCancellationNotification,
    RegistrationConfirmationNotification,
)
from ...transports import email
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
        session_count = self.rsvp.project.session_count
        if session_count:
            return [
                email.EmailAttachment(
                    content=schedule_ical(self.rsvp.project, self.rsvp),
                    filename='event.ics',
                    mimetype=(
                        'text/calendar' if session_count == 1 else 'application/ics'
                    ),
                )
            ]
        return None


@RegistrationConfirmationNotification.renderer
class RenderRegistrationConfirmationNotification(RegistrationBase, RenderNotification):
    """Notify the participant when they register."""

    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you have registered for this project.")

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

    def sms(self):
        return _("You have registered for {project} {url}").format(
            project=self.rsvp.project.joined_title('>'),
            url=self.rsvp.project.url_for(_external=True),
        )


@RegistrationCancellationNotification.renderer
class RenderRegistrationCancellationNotification(RegistrationBase, RenderNotification):
    """Notify the participant when they cancel registration."""

    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you had registered for this project.")

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

    def sms(self):
        return _("You have cancelled your registration for {project}").format(
            project=self.rsvp.project.joined_title('>'),
        )
