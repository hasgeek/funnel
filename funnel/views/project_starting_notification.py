from flask import render_template

from baseframe import _, __

from ..models import ProjectStartingNotification
from .notification import RenderNotification


@ProjectStartingNotification.renderer
class RenderProjectStartingNotification(RenderNotification):
    """Notify crew and participants when the project's schedule is about to start."""

    aliases = {'document': 'project'}

    reason = __("You are receiving this because you have registered for this project.")

    def web(self):
        return render_template(
            'notifications/project_starting_web.html.jinja2', view=self
        )

    def email_subject(self):
        return _("⏰ Starting now! {project}").format(
            project=self.project.joined_title()
        )

    def email_content(self):
        return render_template(
            'notifications/project_starting_email.html.jinja2', view=self
        )

    def sms(self):
        return _("Starting now! {project} {url}").format(
            project=self.project.joined_title('>'),
            url=self.project.url_for(_external=True),
        )
