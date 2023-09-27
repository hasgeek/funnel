"""Account notifications."""

from __future__ import annotations

from flask import render_template

from baseframe import _, __

from ... import app
from ...models import Account, AccountPasswordNotification
from ...transports.sms import SmsTemplate
from ..notification import RenderNotification


class PasswordResetNotificationTemplate(SmsTemplate):
    """DLT registered template for Password Reset."""

    registered_template = (
        "Your password has been updated. If this was not authorized,"
        " reset your password or contact support at {#var#}."
        "\n\nhttps://bye.li to unsubscribe -Hasgeek"
    )
    template = (
        "Your password has been updated. If this was not authorized,"
        " reset your password or contact support at {email}."
        "\n\nhttps://bye.li to unsubscribe -Hasgeek"
    )
    plaintext_template = (
        "Your password has been updated. If this was not authorized,"
        " reset your password or contact support at {email}."
    )

    email: str


@AccountPasswordNotification.renderer
class RenderAccountPasswordNotification(RenderNotification):
    """Notify user when their password is changed."""

    user: Account
    aliases = {'document': 'user'}
    emoji_prefix = "⚠️ "
    hero_image = 'img/email/chars-v1/password.png'
    email_heading = __("Password updated!")

    @property
    def actor(self):
        # This notification won't have an actor when dispatched from password reset.
        # i.e., self.notification.created_by is None. However, password reset is
        # presumably performed by the owner of the user account, i.e., self.document, so
        # we use that as the actor instead, here via the `user` alias (as specified
        # above).
        return self.user

    def web(self):
        return render_template(
            'notifications/user_password_set_web.html.jinja2', view=self
        )

    def email_subject(self):
        return self.emoji_prefix + _("Your password has been updated")

    def email_content(self):
        return render_template(
            'notifications/user_password_set_email.html.jinja2', view=self
        )

    def sms(self) -> PasswordResetNotificationTemplate:
        return PasswordResetNotificationTemplate(
            email=app.config.get('SITE_SUPPORT_EMAIL')
        )
