from flask import render_template

from baseframe import _, __

from ..models import (
    RegistrationCancellationNotification,
    RegistrationConfirmationNotification,
)
from ..transports import email
from .notification import RenderNotification
from .schedule import schedule_ical


@RegistrationConfirmationNotification.renderer
class RenderRegistrationConfirmationNotification(RenderNotification):
    """Notify the participant when they register."""

    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you have registered for this project.")

    def web(self):
        return render_template('notifications/rsvp_yes_web.html.jinja2', view=self)

    def email_subject(self):
        return _("🎟️ Registration confirmation for {project}").format(
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

    def email_attachments(self):
        # Attach a vCalendar of schedule, but only if there are sessions.
        if self.rsvp.project.schedule_start_at:
            return [
                email.EmailAttachment(
                    content=schedule_ical(self.rsvp.project),
                    filename=f'{self.rsvp.project.name}.ics',
                    mimetype='text/calendar',
                )
            ]
        return None

    def sms(self):
        return _("You have registered for {project}. {url}").format(
            project=self.rsvp.project.joined_title('>'),
            url=self.rsvp.project.url_for(_external=True),
        )


@RegistrationCancellationNotification.renderer
class RenderRegistrationCancellationNotification(RenderNotification):
    """Notify the participant when they cancel registration."""

    aliases = {'document': 'rsvp'}

    reason = __("You are receiving this because you had registered for this project.")

    def web(self):
        return render_template('notifications/rsvp_no_web.html.jinja2', view=self)

    def email_subject(self):
        return _("🎫 Registration cancelled for {project}").format(
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
        return _("You have cancelled your registration for {project}.").format(
            project=self.rsvp.project.joined_title('>'),
        )
