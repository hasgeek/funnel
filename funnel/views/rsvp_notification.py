from flask import render_template

from baseframe import _

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

    # self.document is Rsvp instance

    def web(self):
        return render_template(
            'notifications/rsvp_yes_web.html.jinja2',
            view=self,
            project=self.document.project,
        )

    def email_subject(self):
        return _("Registration confirmation for {project}").format(
            project=self.document.project.title
        )

    def email_content(self):
        # FIXME: Move into folder, rename to match notification type, and use 'actor'
        return render_template(
            'notifications/rsvp_yes_email.html.jinja2',
            view=self,
            actor=self.document.user,
            project=self.document.project,
        )

    def email_attachments(self):
        # Attach a vCalendar of schedule, but only if there are sessions.
        if self.document.project.schedule_start_at:
            return [
                email.EmailAttachment(
                    content=schedule_ical(self.document.project),
                    filename=f'{self.document.project.name}.ics',
                    mimetype='text/calendar',
                )
            ]

    def sms(self):
        return _("You have registered for {project}. To stop: {unsubscribe}").format(
            project=self.document.project.title,
            unsubscribe=self.unsubscribe_short_url(),
        )


@RegistrationCancellationNotification.renderer
class RenderRegistrationCancellationNotification(RenderNotification):
    """Notify the participant when they cancel registration."""

    # self.document is Rsvp instance

    def web(self):
        return render_template(
            'notifications/rsvp_no_web.html.jinja2',
            view=self,
            project=self.document.project,
        )

    def email_subject(self):
        return _("Registration cancelled for {project}").format(
            project=self.document.project.title
        )

    def email_content(self):
        return render_template(
            'notifications/rsvp_no_email.html.jinja2',
            view=self,
            actor=self.document.user,
            project=self.document.project,
        )

    def sms(self):
        return _(
            "You have cancelled your registration for {project}. To stop: {unsubscribe}"
        ).format(
            project=self.document.project.title,
            unsubscribe=self.unsubscribe_short_url(),
        )
