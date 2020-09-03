from flask import render_template

from baseframe import _, __
from baseframe.filters import time_filter

from ...models import ProjectStartingNotification
from ..helpers import shortlink
from ..notification import RenderNotification


@ProjectStartingNotification.renderer
class RenderProjectStartingNotification(RenderNotification):
    """Notify crew and participants when the project's schedule is about to start."""

    aliases = {'document': 'project', 'fragment': 'session'}
    emoji_prefix = "⏰ "
    reason = __("You are receiving this because you have registered for this project")

    def web(self):
        return render_template(
            'notifications/project_starting_web.html.jinja2', view=self
        )

    def email_subject(self):
        return self.emoji_prefix + _("{project} starts at {time}").format(
            project=self.project.joined_title(),
            time=time_filter(self.session.start_at_localized),
        )

    def email_content(self):
        return render_template(
            'notifications/project_starting_email.html.jinja2', view=self
        )

    def sms(self):
        return _("{project} starts at {time} {url}").format(
            project=self.project.joined_title('>'),
            time=time_filter(self.session.start_at_localized),
            url=shortlink(self.project.url_for(_external=True)),
        )
