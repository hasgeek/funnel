from flask import render_template

from baseframe import _, __

from ..models import NewUpdateNotification
from .notification import RenderNotification


@NewUpdateNotification.renderer
class RenderNewUpdateNotification(RenderNotification):
    """Notify crew and participants when the project has a new update."""

    aliases = {'document': 'update'}

    reason = __("You are receiving this because you have registered for this project.")

    def web(self):
        return render_template('notifications/update_new_web.html.jinja2', view=self)

    def email_subject(self):
        return _("📰 {update} ({project})").format(
            update=self.update.title, project=self.update.project.joined_title()
        )

    def email_content(self):
        return render_template('notifications/update_new_email.html.jinja2', view=self)

    def sms(self):
        return _("Update in {project}: {update} {url}").format(
            project=self.update.project.joined_title('>'),
            update=self.update.title,
            url=self.update.url_for(_external=True),
        )
