"""Account notifications."""

from __future__ import annotations

from flask import render_template, url_for

from baseframe import _, __

from ... import app
from ...models import Account, AccountPasswordNotification
from ...transports.sms import OneLineTemplate
from ..helpers import shortlink
from ..notification import RenderNotification


@AccountPasswordNotification.renderer
class RenderAccountPasswordNotification(RenderNotification):
    """Notify user when their password is changed."""

    user: Account
    aliases = {'document': 'user'}
    emoji_prefix = "⚠️ "
    hero_image = 'img/email/chars-v1/password.png'
    email_heading = __("Password updated!")

    @property
    def actor(self) -> Account:
        # This notification won't have an actor when dispatched from password reset.
        # i.e., self.notification.created_by is None. However, password reset is
        # presumably performed by the owner of the user account, i.e., self.document, so
        # we use that as the actor instead, here via the `user` alias (as specified
        # above).
        return self.user

    def web(self) -> str:
        return render_template(
            'notifications/user_password_set_web.html.jinja2', view=self
        )

    def email_subject(self) -> str:
        return self.emoji_prefix + _("Your password has been updated")

    def email_content(self) -> str:
        return render_template(
            'notifications/user_password_set_email.html.jinja2', view=self
        )

    def sms(self) -> OneLineTemplate:
        return OneLineTemplate(
            text1=_(
                "Your password has been updated. If this was not authorized, reset"
                " your password or contact support at {email}."
            ).format(email=app.config['SITE_SUPPORT_EMAIL']),
            url=shortlink(
                url_for('reset', _external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
