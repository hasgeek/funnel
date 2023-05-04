"""Project update notifications."""

from __future__ import annotations

from flask import render_template

from baseframe import _, __

from ...models import NewUpdateNotification, Update
from ...transports.sms import TwoLineTemplate
from ..helpers import shortlink
from ..notification import RenderNotification


@NewUpdateNotification.renderer
class RenderNewUpdateNotification(RenderNotification):
    """Notify crew and participants when the project has a new update."""

    update: Update
    aliases = {'document': 'update'}
    emoji_prefix = "📰 "
    reason = __("You are receiving this because you have registered for this project")
    hero_image = "https://images.hasgeek.com/embed/file/85250bc8f2534f5cb4a5d3d4f97c2eb9?size=196x190"
    email_title = "New update!"

    @property
    def actor(self):
        """
        Return author of the update.

        Updates may be written by one user and published by another. The notification's
        default actor is the publisher as they caused it to be dispatched, but in this
        case the actor of interest is the author of the update.
        """
        return self.update.user

    def web(self):
        return render_template('notifications/update_new_web.html.jinja2', view=self)

    def email_subject(self):
        return self.emoji_prefix + _("{update} ({project})").format(
            update=self.update.title, project=self.update.project.joined_title
        )

    def email_content(self):
        return render_template('notifications/update_new_email.html.jinja2', view=self)

    def sms(self) -> TwoLineTemplate:
        return TwoLineTemplate(
            text1=_("Update in {project}:").format(
                project=self.update.project.joined_title
            ),
            text2=self.update.title,
            url=shortlink(
                self.update.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
