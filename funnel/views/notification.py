from collections import defaultdict
from itertools import filterfalse, zip_longest
from uuid import uuid4

from flask_babelhg import force_locale

from coaster.auth import current_auth

from .. import app, rq
from ..models import Notification, UserNotification, db
from ..serializers import token_serializer
from ..transports import platform_transports
from ..transports.email import send_email

__all__ = ['NotificationView', 'dispatch_notification']


@UserNotification.views('render')
def render_user_notification(obj):
    return Notification.renderers[obj.notification.cls_type](obj.notification).web(obj)


class NotificationView:
    """
    Base class for rendering user notifications, with support methods.

    Subclasses must override the render methods:

    * :meth:`web`
    * :meth:`email`, :meth:`email_subject` and :meth:`email_attachments`
    * :meth:`sms`
    * :meth:`webpush`
    * :meth:`telegram`
    * :meth:`whatsapp`

    Subclasses must be registered against the specific notification type like this::

        @MyNotification.renderer
        class MyNotificationView(NotificationView):
            ...
    """

    def __init__(self, user_notification):
        self.user_notification = user_notification
        self.notification = user_notification.notification

    def unsubscribe_token(self, transport):
        """
        Return a token suitable for use in an unsubscribe link.

        The token only contains a user id (``user.buid`` here) and notification type
        (for ``user.notification_preferences``). The template should wrap this token
        with ``?utm_campaign=unsubscribe&utm_source={notification.eventid}``. Since
        tokens are sensitive, the view will strip them out of the URL before rendering
        the page, using a similar mechanism to that used for account reset.
        """
        # This payload is consumed by :meth:`AccountNotificationView.unsubscribe`
        return token_serializer().dumps(
            {
                'buid': self.user_notification.user.buid,
                'notification_type': self.notification.type,
                'transport': transport,
            }
        )

    # --- Overrideable render methods

    def web(self):
        """
        Render for display on the website.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `web`")

    def email(self):
        """
        Render an email update, suitable for handing over to send_email.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `email`")

    def email_subject(self):
        """
        Render the subject of an email update, suitable for handing over to send_email.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `email_subject`")

    def email_attachments(self):
        """Render optional attachments to an email notification."""
        return None

    def sms(self):
        """
        Render a short text message. Templates must use a single line with a link.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `sms`")

    def webpush(self):
        """
        Render a web push notification.

        Default implementation uses SMS render.
        """
        return self.sms(self)

    def telegram(self):
        """
        Render a Telegram HTML message.

        Default implementation uses SMS render.
        """
        return self.sms(self)

    def whatsapp(self):
        """
        Render a WhatsApp-formatted text message.

        Default implementation uses SMS render.
        """
        return self.sms(self)


# --- Dispatch functions ---------------------------------------------------------------

# This has four parts:
# 1. Front function `dispatch_notification` is called from views or signal handlers. It
#    receives Notification instances that already have document and fragment set on
#    them, and updates them to have a common eventid and user_id, then queues
#    a background job, taking care to preserve the priority order.
# 2. The first background worker loads these notifications in turn, extracts
#    UserNotification instances into batches of DISPATCH_BATCH_SIZE, and then passes
#    them into yet another background worker.
# 3. Second background worker performs a roll-up on each UserNotification, then queues
#    a background job for each eligible transport.
# 4. Third set of per-transport background workers deliver one message each.


def dispatch_notification(*notifications):
    """
    Dispatches one or more notifications. Usage::

        dispatch_notification(
            MyNotification(document=doc, fragment=None),
            MyOtherNotification(document=doc, fragment=frag)
        )

    This function performs a database commit to ensure notifications are available to
    background jobs, so it must only be called when it's safe to commit.
    """
    eventid = uuid4()  # Create a single eventid
    for notification in notifications:
        if not isinstance(notification, Notification):
            raise TypeError(f"Not a notification: {notification!r}")
        notification.eventid = eventid
        notification.user = current_auth.user
    db.session.commit()
    dispatch_notification_job.queue(
        eventid, [notification.id for notification in notifications]
    )


# --- Transports -----------------------------------------------------------------------


@rq.job('funnel')
def dispatch_transport_email(user_notification_ids):
    with app.app_context():
        queue = [
            UserNotification.query.get(identity) for identity in user_notification_ids
        ]
        for user_notification in queue:
            with force_locale(user_notification.user.locale or 'en'):
                view = Notification.renderers[user_notification.notification.type](
                    user_notification
                )
                subject = view.email_subject()
                content = view.email()
                attachments = view.email_attachments(user_notification)
                user_notification.messageid_email = send_email(
                    subject=subject,
                    to=[
                        (
                            user_notification.user.fullname,
                            user_notification.user.transport_for_email(
                                user_notification.notification.preference_context
                            ),
                        )
                    ],
                    content=content,
                    attachments=attachments,
                )


# Add transport workers here as their worker methods are written
transport_workers = {'email': dispatch_transport_email}

# --- Notification background workers --------------------------------------------------

DISPATCH_BATCH_SIZE = 10


@rq.job('funnel')
def dispatch_notification_job(eventid, notification_ids):
    with app.app_context():
        notifications = [
            Notification.query.get((eventid, nid)) for nid in notification_ids
        ]

        # Dispatch, creating batches of DISPATCH_BATCH_SIZE each
        for notification in notifications:
            for batch in (
                filterfalse(lambda x: x is None, unfiltered_batch)
                for unfiltered_batch in zip_longest(
                    *[notification.dispatch()] * DISPATCH_BATCH_SIZE, fillvalue=None
                )
            ):
                db.session.commit()
                dispatch_user_notifications_job.queue(
                    [user_notification.identity for user_notification in batch],
                )

        # How does this batching work? There is a confusing recipe in the itertools
        # module documentation. Here is what happens:
        #
        # `notification.dispatch()` returns a generator. We make a list of the
        # desired batch size containing repeated references to the same generator.
        # This works because Python lists can contain the same item multiple times,
        # and ``[item] * 2 == [item, item]`` (also: ``[1, 2] * 2 = [1, 2, 1, 2]``).
        # These copies are fed as positional parameters to `zip_longest`, which
        # returns a batch containing one item from each of its parameters. For each
        # batch (size 10 from the constant defined above), we commit to database
        # and then queue a background job to deliver to them. When `zip_longest`
        # runs out of items, it returns a batch padded with the `fillvalue` None.
        # We use `filterfalse` to discard these None values. This difference
        # distinguishes `zip_longest` from `zip`, which truncates the source data
        # when it is short of a full batch.
        #
        # Discussion of approaches at https://stackoverflow.com/q/8290397/78903


@rq.job('funnel')
def dispatch_user_notifications_job(user_notification_ids):
    with app.app_context():
        queue = [
            UserNotification.query.get(identity) for identity in user_notification_ids
        ]
        transport_batch = defaultdict(list)

        for user_notification in queue:
            user_notification.rollup_previous()
            for transport in transport_workers:
                if platform_transports[transport] and user_notification.has_transport(
                    transport
                ):
                    transport_batch[transport].append(user_notification.identity)
        db.session.commit()
        for transport, batch in transport_batch.items():
            # Based on user preferences, a transport may have no recipients at all.
            # Only queue a background job when there is work to do.
            if batch:
                transport_workers[transport].queue(batch)
