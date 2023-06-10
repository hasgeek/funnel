"""Project starting notification."""

from __future__ import annotations

from typing import Optional

from flask import render_template

from baseframe import _, __
from baseframe.filters import time_filter

from ...models import Project, ProjectStartingNotification, Session
from ...transports.sms import SmsTemplate
from ..helpers import shortlink
from ..notification import RenderNotification


class ProjectStartingTemplate(SmsTemplate):
    registered_template = 'Reminder: {#var#} is starting soon. Join at {#var#}\n\nhttps://bye.li to stop - Hasgeek'
    template = 'Reminder: {project} is starting soon. Join at {url}\n\nhttps://bye.li to stop - Hasgeek'
    plaintext_template = 'Reminder: {project} is starting soon. Join at {url}'

    project: str
    url: str

    def available_var_len(self):
        """Discount the two URLs from available length."""
        return self.template_var_len - len(self.url) - len(self.unsubscribe_url)

    def truncate(self) -> None:
        """Truncate text1 to fit."""
        max_text_length = self.available_var_len()
        if len(self.project) > max_text_length:
            self.project = self.project[: max_text_length - 1] + '…'


@ProjectStartingNotification.renderer
class RenderProjectStartingNotification(RenderNotification):
    """Notify crew and participants when the project's schedule is about to start."""

    project: Project
    session: Optional[Session]
    aliases = {'document': 'project', 'fragment': 'session'}
    emoji_prefix = "⏰ "
    reason = __("You are receiving this because you have registered for this project")

    def web(self):
        return render_template(
            'notifications/project_starting_web.html.jinja2', view=self
        )

    def email_subject(self):
        return self.emoji_prefix + _("{project} starts at {time}").format(
            project=self.project.joined_title,
            time=time_filter((self.session or self.project).start_at_localized),
        )

    def email_content(self):
        return render_template(
            'notifications/project_starting_email.html.jinja2', view=self
        )

    def sms(self) -> SmsTemplate:
        return ProjectStartingTemplate(
            project=self.project.joined_title,
            url=shortlink(
                self.project.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
