from flask import render_template

from baseframe import _, __

from ..models import NewUpdateNotification
from .notification import RenderNotification


@NewUpdateNotification.renderer
class RenderNewUpdateNotification(RenderNotification):
    """Notify crew and participants when the project has a new update."""

    aliases = {'document': 'update'}

    reason = __("You are receiving this because you have registered for this project.")

    @property
    def actor(self):
        """
        Updates may be written by one user and published by another. The notification's
        default actor is the publisher as they caused it to be dispatched, but in this
        case the actor of interest is the author of the update.
        """
        return self.update.user

    def web(self):
        return render_template('notifications/update_new_web.html.jinja2', view=self)

    def email_subject(self):
        return _("📰 {update} ({project})").format(
            update=self.update.title, project=self.update.project.joined_title()
        )

    def email_content(self):
        return render_template('notifications/update_new_email.html.jinja2', view=self)

    def sms(self):
        return _("Hi! Update in {project}: {update} {url}").format(
            project=self.update.project.joined_title('>'),
            update=self.update.title,
            url=self.update.url_for(_external=True),
        )
