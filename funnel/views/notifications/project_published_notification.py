"""Project published notification."""

from __future__ import annotations

from flask import render_template

from baseframe import _, __

from ...models import Project, ProjectPublishedNotification
from ...transports.sms import SmsTemplate
from ..helpers import shortlink
from ..notification import RenderNotification
from .mixins import TemplateVarMixin


class ProjectPublishedTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for Project published."""

    registered_template = (
        "{#var#}, whose event you previously registered for, has just announced"
        " {#var#}. Details here: {#var#}\n\nhttps://bye.li to stop -Hasgeek"
    )
    template = (
        "{profile}, whose event you previously registered for, has just announced"
        "{project}. Details here: {url}\n\nhttps://bye.li to stop -Hasgeek"
    )
    plaintext_template = "{profile} has published a new project: {url}"

    url: str
    profile: str


@ProjectPublishedNotification.renderer
class RenderProjectPublishedNotification(RenderNotification):
    """Notify account followers when a new project is published."""

    project: Project
    aliases = {'document': 'project'}
    emoji_prefix = "📰 "
    reason = __(
        "You are receiving this because you have registered for this or related"
        " projects"
    )

    @property
    def actor(self):
        return self.project.user

    def web(self):
        return render_template('notifications/update_new_web.html.jinja2', view=self)

    def email_subject(self):
        return self.emoji_prefix + _("{update} ({project})").format(
            update=self.project.title, project=self.project.joined_title
        )

    def email_content(self):
        return render_template(
            'notifications/project_published_email.html.jinja2', view=self
        )

    def sms(self) -> ProjectPublishedTemplate:
        return ProjectPublishedTemplate(
            profile=self.project.profile,
            project=self.project,
            url=shortlink(
                self.update.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
