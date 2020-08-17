from itertools import filterfalse, zip_longest
from uuid import uuid4

from flask_babelhg import force_locale

from coaster.auth import current_auth

from .. import app, rq
from ..models import Notification, UserNotification, db, notification_type_registry

__all__ = ['NotificationView', 'dispatch_notification']


class NotificationView:
    """
    Base class for rendering notifications.

    Subclasses must override the render methods, currently :meth:`web`, :meth:`email`,
    :meth:`sms`, :meth:`webpush`, :meth:`telegram`, :meth:`whatsapp`.

    Subclasses must be registered against the specific notification type like this::

        @MyNotification.renderer
        class MyNotificationView(NotificationView):
            ...

    Also provides support methods for generating unsubscribe links.
    """

    def __init__(self, obj):
        self.notification = obj

    def dispatch_for(self, user_notification, transport):
        """Method that does the actual sending."""
        # TODO: Insert dispatch code here

    # --- Overrideable render methods

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

    def email_attachments(self, user_notification):
        """Render optional attachments to an email notification."""
        return None

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


# --- Dispatch functions ---------------------------------------------------------------

# This has three parts:
# 1. Front function dispatch_notification is called from views or signal handlers
# 2. This queues a background job to process the notification, in two parts.
# 3. First part (RQ job) creates the Notification subtype instances and calls their
#    dispatch methods to retrive the UserNotification instances. It commits them to db,
#    then passes their ids into a series of batched jobs.
# 4. Second part (RQ jobs) processes each batch of UserNotification methods, calling
#    NotificationView.dispatch (or its replacement subclass), which is responsible for
#    the actual dispatch.


def dispatch_notification(notification_types, document, target=None):
    if isinstance(notification_types, Notification):
        notification_types = [Notification]
    for cls in notification_types:
        if not isinstance(document, cls.document_model):
            raise TypeError(
                "Notification document is of incorrect type for %s" % cls.__name__
            )
        if target is not None and not isinstance(target, cls.target_model):
            raise TypeError(
                "Notification target is of incorrect type for %s" % cls.__name__
            )
    dispatch_notification_job.queue(
        [ntype.cls_type for ntype in notification_types],
        user_id=current_auth.user.id if current_auth.user else None,
        document_uuid=document.uuid,
        target_uuid=target.uuid if target is not None else None,
    )


DISPATCH_BATCH_SIZE = 10


@rq.job('funnel')
def dispatch_notification_job(ntypes, user_id, document_uuid, target_uuid):
    with app.app_context():
        eventid = uuid4()  # Create a single eventid
        event_notifications = [
            notification_type_registry[ntype](
                user_id=user_id,
                eventid=eventid,
                document_uuid=document_uuid,
                target_uuid=target_uuid,
            )
            for ntype in ntypes
        ]

        # Commit notifications before dispatching
        for notification in event_notifications:
            db.session.add(notification)
        db.session.commit()

        # Dispatch, creating batches of DISPATCH_BATCH_SIZE each
        for notification in event_notifications:
            for batch in (
                filterfalse(lambda x: x is None, unfiltered_batch)
                for unfiltered_batch in zip_longest(
                    *[notification.dispatch()] * DISPATCH_BATCH_SIZE, fillvalue=None
                )
            ):
                db.session.commit()
                dispatch_user_notifications_job.queue(
                    None,  # TODO per-transport batching
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
def dispatch_user_notifications_job(transport, user_notification_ids):
    with app.app_context():
        for identity in user_notification_ids:
            # query.get() here cannot fail. If it does, something is wrong elsewhere.
            user_notification = UserNotification.query.get(identity)
            with force_locale(user_notification.user.locale or 'en'):
                user_notification.dispatch_for(transport)
            # Commit after each recipient to protect from dispatch failure
            db.session.commit()
