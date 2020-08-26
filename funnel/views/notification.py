from collections import defaultdict
from datetime import datetime
from functools import wraps
from itertools import filterfalse, zip_longest
from uuid import uuid4

from flask import url_for

from flask_babelhg import force_locale

from baseframe import _, __, statsd
from coaster.auth import current_auth

from .. import app, rq
from ..models import Notification, UserNotification, db
from ..serializers import token_serializer
from ..transports import TransportError, email, platform_transports, sms
from .helpers import make_cached_token

__all__ = ['RenderNotification', 'dispatch_notification']


@UserNotification.views('render')
def render_user_notification(obj):
    return Notification.renderers[obj.notification.type](obj).web()


class RenderNotification:
    """
    Base class for rendering user notifications, with support methods.

    Subclasses must override the render methods:

    * :meth:`web`
    * :meth:`email_subject`, :meth:`email_content` and :meth:`email_attachments`
    * :meth:`sms`
    * :meth:`webpush`
    * :meth:`telegram`
    * :meth:`whatsapp`

    Subclasses must be registered against the specific notification type like this::

        @MyNotification.renderer
        class MyNotificationView(NotificationView):
            ...
    """

    #: Reason specified in email templates. Subclasses MAY override
    reason = __("You are receiving this because you have an account at hasgeek.com.")

    #: Copies of reason per transport that can be overriden by subclasses
    reason_email = reason
    reason_sms = reason
    reason_webpush = reason
    reason_telegram = reason
    reason_whatsapp = reason

    #: Aliases for document and fragment, to make render methods clearer
    aliases = {}

    def __init__(self, user_notification):
        self.user_notification = user_notification
        self.notification = user_notification.notification
        self.document = user_notification.notification.document
        self.fragment = user_notification.notification.fragment
        if 'document' in self.aliases:
            setattr(self, self.aliases['document'], self.document)
        if 'fragment' in self.aliases:
            setattr(self, self.aliases['fragment'], self.fragment)

    def transport_for(self, transport):
        """
        Return the transport address for the notification.

        Subclasses may override this if they need to enforce a specific transport
        address, such as verification tokens sent to a specific email address or phone
        number. Since notifications cannot have data, the notification will have to be
        raised on the address document (eg: UserEmail, UserPhone, EmailAddress).
        """
        return self.user_notification.user.transport_for(
            transport, self.notification.preference_context
        )

    def unsubscribe_token(self, transport):
        """
        Return a token suitable for use in an unsubscribe link.

        The token contains:

        1. The user id (``user.buid`` for now)
        2. The notification type (for ``user.notification_preferences``)
        3. The transport (for attribute to unset), and
        4. The transport hash, for identifying the source.

        The template should wrap this token with ``utm_campaign=unsubscribe`` and
        ``utm_source={notification.eventid}``. Since tokens are sensitive, the view will
        strip them out of the URL before rendering the page, using a similar mechanism
        to that used for account reset.
        """
        # This payload is consumed by :meth:`AccountNotificationView.unsubscribe`
        return token_serializer().dumps(
            {
                'buid': self.user_notification.user.buid,
                'notification_type': self.notification.type,
                'transport': transport,
                'hash': self.transport_for(transport).transport_hash,
            }
        )

    def unsubscribe_url(self, transport):
        """Return an unsubscribe URL."""
        return url_for(
            'notification_unsubscribe',
            token=self.unsubscribe_token(transport=transport),
            _external=True,
            utm_campaign='unsubscribe',
            utm_medium=transport,
            utm_source=self.notification.eventid,
        )

    def unsubscribe_short_url(self, transport='sms'):
        """Return a short but temporary unsubscribe URL (for SMS)."""
        # Eventid is included here because SMS links can't have utm_* tags.
        # However, the current implementation of the unsubscribe handler doesn't
        # use this, and can't add utm_* tags to the URL as it only examines the token
        # after cleaning up the URL, so there are no more redirects left.
        token = make_cached_token(
            {
                'buid': self.user_notification.user.buid,
                'notification_type': self.notification.type,
                'transport': transport,
                'hash': self.transport_for(transport).transport_hash,
                'eventid': self.notification.eventid,
                'timestamp': datetime.utcnow(),  # Naive timestamp
            },
            timeout=14 * 24 * 60 * 60,  # Reserve generated token for 14 days
        )
        unsubscribe_domain = app.config.get('UNSUBSCRIBE_DOMAIN')
        if unsubscribe_domain:
            # For this to work, a web server must listen on the unsubscribe domain and
            # redirect all paths to url_for('notification_unsubscribe_short') + path
            return 'https://' + unsubscribe_domain + '/' + token
        return url_for('notification_unsubscribe_short', token=token, _external=True)

    # --- Overrideable render methods

    @property
    def actor(self):
        """The actor that prompted this notification. May be overriden."""
        return self.notification.user

    def web(self):
        """
        Render for display on the website.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `web`")

    def email_subject(self):
        """
        Render the subject of an email update, suitable for handing over to send_email.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `email_subject`")

    def email_content(self):
        """
        Render an email update, suitable for handing over to send_email.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `email_content`")

    def email_attachments(self):
        """Render optional attachments to an email notification."""
        return None

    def sms(self):
        """
        Render a short text message. Templates must use a single line with a link.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `sms`")

    def sms_with_unsubscribe(self):
        """Add an unsubscribe link to the SMS message."""
        return (
            self.sms()
            + ' '
            + _("To stop: {unsubscribe}").format(
                unsubscribe=self.unsubscribe_short_url('sms')
            )
        )

    def webpush(self):
        """
        Render a web push notification.

        Default implementation uses SMS render.
        """
        return self.sms()

    def telegram(self):
        """
        Render a Telegram HTML message.

        Default implementation uses SMS render.
        """
        return self.sms()

    def whatsapp(self):
        """
        Render a WhatsApp-formatted text message.

        Default implementation uses SMS render.
        """
        return self.sms()


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
        db.session.add(notification)
    db.session.commit()
    dispatch_notification_job.queue(
        eventid, [notification.id for notification in notifications]
    )
    for notification in notifications:
        statsd.incr(
            'notification.dispatch', tags={'notification_type': notification.type}
        )


# --- Transports -----------------------------------------------------------------------


def transport_worker_wrapper(func):
    @wraps(func)
    def inner(user_notification_ids):
        with app.test_request_context():  # Views may need request.url_root
            queue = [
                UserNotification.query.get(identity)
                for identity in user_notification_ids
            ]
            for user_notification in queue:
                # The notification may be revoked by the time this worker processes it.
                # If so, skip it.
                if not user_notification.is_revoked:
                    with force_locale(user_notification.user.locale or 'en'):
                        view = Notification.renderers[
                            user_notification.notification.type
                        ](user_notification)
                        try:
                            func(user_notification, view)
                            db.session.commit()
                        except TransportError:
                            if user_notification.notification.ignore_transport_errors:
                                pass
                            else:
                                # TODO: Implement transport error handling code here
                                raise

    return inner


@rq.job('funnel')
@transport_worker_wrapper
def dispatch_transport_email(user_notification, view):
    if not user_notification.user.main_notification_preferences.by_transport('email'):
        # Cancel delivery if user's main switch is off. This was already checked, but
        # the worker may be delayed and the user may have changed their preference.
        user_notification.messageid_email = 'cancelled'
        return
    address = view.transport_for('email')
    subject = view.email_subject()
    content = view.email_content()
    attachments = view.email_attachments()
    user_notification.messageid_email = email.send_email(
        subject=subject,
        to=[(user_notification.user.fullname, str(address))],
        content=content,
        attachments=attachments,
    )
    statsd.incr(
        'notification.transport',
        tags={
            'notification_type': user_notification.notification_type,
            'transport': 'email',
        },
    )


@rq.job('funnel')
@transport_worker_wrapper
def dispatch_transport_sms(user_notification, view):
    if not user_notification.user.main_notification_preferences.by_transport('sms'):
        # Cancel delivery if user's main switch is off. This was already checked, but
        # the worker may be delayed and the user may have changed their preference.
        user_notification.messageid_sms = 'cancelled'
        return
    user_notification.messageid_sms = sms.send(
        str(view.transport_for('sms')), view.sms_with_unsubscribe(),
    )
    statsd.incr(
        'notification.transport',
        tags={
            'notification_type': user_notification.notification_type,
            'transport': 'sms',
        },
    )


# Add transport workers here as their worker methods are written
transport_workers = {'email': dispatch_transport_email, 'sms': dispatch_transport_sms}

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
                notification_ids = [
                    user_notification.identity for user_notification in batch
                ]
                dispatch_user_notifications_job.queue(notification_ids)
                statsd.incr(
                    'notification.recipient',
                    count=len(notification_ids),
                    tags={'notification_type': notification.type},
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
