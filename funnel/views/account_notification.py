from flask import render_template, url_for

from baseframe import _

from .. import app
from ..models import AccountPasswordNotification
from .notification import RenderNotification


@AccountPasswordNotification.renderer
class RenderAccountPasswordNotification(RenderNotification):
    """Notify user when their password is changed."""

    aliases = {'document': 'user'}
    emoji_prefix = "⚠️ "

    @property
    def actor(self):
        """This notification won't have an actor when dispatched from password reset."""
        return self.document

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

    def sms(self):
        return _(
            "Your password has been updated. If this was not authorized, reset your"
            " password or contact support at {email}. {reset_url}"
        ).format(email=app.config['SITE_SUPPORT_EMAIL'], reset_url=url_for('reset'))
