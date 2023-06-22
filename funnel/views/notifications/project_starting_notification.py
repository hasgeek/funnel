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
from .mixins import ProjectTemplateMixin


class ProjectStartingTemplate(ProjectTemplateMixin, SmsTemplate):
    """DLT registered template for project starting notification."""

    registered_template = (
        'Reminder: {#var#} is starting soon. Join at {#var#}'
        '\n\nhttps://bye.li to stop - Hasgeek'
    )
    template = (
        "Reminder: {project_title} is starting soon. Join at {url}"
        "\n\nhttps://bye.li to stop - Hasgeek"
    )
    plaintext_template = "Reminder: {project_title} is starting soon. Join at {url}"

    project_only: str
    url: str


@ProjectStartingNotification.renderer
class RenderProjectStartingNotification(RenderNotification):
    """Notify crew and participants when the project's schedule is about to start."""

    project: Project
    session: Optional[Session]
    aliases = {'document': 'project', 'fragment': 'session'}
    emoji_prefix = "⏰ "
    reason = __("You are receiving this because you have registered for this project")
    hero_image = 'https://images.hasgeek.com/embed/file/c8a0cea54b444fa7891fe8369e1aa768?size=196x151'
    email_heading = __("Session starting soon!")

    def web(self) -> str:
        return render_template(
            'notifications/project_starting_web.html.jinja2', view=self
        )

    def email_subject(self) -> str:
        start_time = (self.session or self.project).start_at_localized
        if start_time is not None:
            return self.emoji_prefix + _("{project} starts at {time}").format(
                project=self.project.joined_title, time=time_filter(start_time)
            )
        return self.emoji_prefix + _("{project} is starting soon").format(
            project=self.project.joined_title
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/project_starting_email.html.jinja2', view=self
        )

    def sms(self) -> ProjectStartingTemplate:
        return ProjectStartingTemplate(
            project=self.project,
            url=shortlink(
                self.project.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
