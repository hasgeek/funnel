from flask import render_template

from baseframe import _

from ..models import SessionStartingNotification
from .notification import RenderNotification


@SessionStartingNotification.renderer
class RenderSessionStartingNotification(RenderNotification):
    """Notify crew and participants when the project has a session about to start."""

    aliases = {'document': 'project'}

    def web(self):
        return render_template(
            'notifications/session_starting_web.html.jinja2', view=self
        )

    def email_subject(self):
        return _("⏰ Starting now! {project}").format(project=self.project.joined_title)

    def email_content(self):
        return render_template(
            'notifications/session_starting_email.html.jinja2', view=self
        )

    def sms(self):
        return _("Starting now! {project} {url}").format(
            project=self.project.joined_title, url=self.project.url_for(_external=True),
        )
