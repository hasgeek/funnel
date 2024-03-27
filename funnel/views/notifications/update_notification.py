"""Project update notifications."""

from __future__ import annotations

from flask import render_template

from baseframe import _, __

from ...models import Account, Project, ProjectUpdateNotification, Update
from ...transports.sms import SmsPriority, SmsTemplate
from ..helpers import shortlink
from ..notification import RenderNotification
from .mixins import TemplateVarMixin


class UpdateMergedTitleTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for updates when the project has a merged title."""

    registered_template = (
        'There is an update in {#var#}: {#var#}\n\nhttps://bye.li to stop -Hasgeek'
    )
    template = (
        "There is an update in {project}: {url}\n\nhttps://bye.li to stop -Hasgeek"
    )
    plaintext_template = "There is an update in {project}: {url}"
    message_priority = SmsPriority.NORMAL

    url: str


class UpdateSplitTitleTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for updates when the project has a split title."""

    registered_template = (
        "There is an update in {#var#} / {#var#}. Details here: {#var#}"
        "\n\nhttps://bye.li to stop -Hasgeek"
    )
    template = (
        "There is an update in {account_title} / {project_title}. Details here: {url}"
        "\n\nhttps://bye.li to stop -Hasgeek"
    )
    plaintext_template = (
        "There is an update in {account_title} / {project_title}: {url}"
    )
    message_priority = SmsPriority.NORMAL

    url: str


@ProjectUpdateNotification.renderer
class RenderProjectUpdateNotification(RenderNotification):
    """Notify crew and participants when the project has a new update."""

    project: Project
    update: Update
    aliases = {'document': 'project', 'fragment': 'update'}
    emoji_prefix = "📰 "
    reason = __(
        "You are receiving this because you have registered for this or related"
        " projects"
    )

    @property
    def actor(self) -> Account:
        """
        Return author of the update.

        Updates may be written by one user and published by another. The notification's
        default actor is the publisher as they caused it to be dispatched, but in this
        case the actor of interest is the author of the update.
        """
        return self.update.created_by

    def web(self) -> str:
        return render_template(
            'notifications/project_update_web.html.jinja2', view=self
        )

    def email_subject(self) -> str:
        return self.emoji_prefix + _("{update} ({project})").format(
            update=self.update.title, project=self.update.project.joined_title
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/project_update_email.html.jinja2', view=self
        )

    def sms(self) -> UpdateMergedTitleTemplate | UpdateSplitTitleTemplate:
        if len(self.update.project.title_parts) == 1:
            return UpdateMergedTitleTemplate(
                project=self.update.project,
                url=shortlink(
                    self.update.url_for(_external=True, **self.tracking_tags('sms')),
                    shorter=True,
                ),
            )
        return UpdateSplitTitleTemplate(
            project_title=self.update.project,
            account_title=self.update.project.account,
            url=shortlink(
                self.update.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
