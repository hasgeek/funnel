from ..models import Notification, UserNotification


@Notification.views('render')
class NotificationRenderView:
    """Base class for rendering notifications. Subclasses must override methods."""

    def __init__(self, obj):
        self.notification = obj

    def web(self, user_notification):
        """
        Render for display on the website.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `web`")

    def email(self, user_notification):
        """
        Render an email update, suitable for handing over to send_email.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `email`")

    def sms(self, user_notification):
        """
        Render a short text message. Templates must use a single line with a link.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `sms`")

    def webpush(self, user_notification):
        """
        Render a web push notification.

        Default implementation uses SMS render.
        """
        return self.sms(self)

    def telegram(self, user_notification):
        """
        Render a Telegram HTML message.

        Default implementation uses SMS render.
        """
        return self.sms(self)

    def whatsapp(self, user_notification):
        """
        Render a WhatsApp-formatted text message.

        Default implementation uses SMS render.
        """
        return self.sms(self)


@UserNotification.views('render')
class UserNotificationRenderView:
    """Support class for rendering user notifications."""

    def web(self):
        """
        Render for display on the website.
        """
        return self.notification.views.render.web(self)

    def email(self):
        """
        Render an email update, suitable for handing over to send_email.
        """
        return self.notification.views.render.email(self)

    def sms(self):
        """
        Render a short text message. Templates must use a single line with a link.
        """
        return self.notification.views.render.sms(self)

    def webpush(self):
        """
        Render a web push notification.
        """
        return self.notification.views.render.webpush(self)

    def telegram(self):
        """
        Render a Telegram HTML message.
        """
        return self.notification.views.render.telegram(self)

    def whatsapp(self):
        """
        Render a WhatsApp-formatted text message.
        """
        return self.notification.views.render.whatsapp(self)
