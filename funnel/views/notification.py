"""Views for sending and rendering notifications."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from email.utils import formataddr
from functools import wraps
from itertools import filterfalse, zip_longest
from typing import Dict, List, Optional
from uuid import uuid4

from flask import url_for
from flask_babel import force_locale
from werkzeug.utils import cached_property

from typing_extensions import Literal

from baseframe import __, statsd
from coaster.auth import current_auth

from .. import app
from ..models import Notification, UserNotification, db
from ..serializers import token_serializer
from ..transports import TransportError, email, platform_transports, sms
from ..transports.sms import SmsTemplate
from .helpers import make_cached_token
from .jobs import rqjob

__all__ = ['RenderNotification', 'dispatch_notification']


@UserNotification.views('render', cached_property=True)
def render_user_notification(obj):
    """Render web notifications for the user."""
    return Notification.renderers[obj.notification.type](obj)


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

    #: Aliases for document and fragment, to make render methods clearer
    aliases: Dict[Literal['document', 'fragment'], str] = {}

    #: Emoji prefix, for transports that support them
    emoji_prefix = ''

    #: Reason specified in email templates. Subclasses MAY override
    reason = __("You are receiving this because you have an account at hasgeek.com")

    #: Copies of reason per transport that can be overriden by subclasses using either
    #: a property or an attribute
    @property
    def reason_for(self):
        return self.reason

    reason_email = reason_for
    reason_sms = reason_for
    reason_webpush = reason_for
    reason_telegram = reason_for
    reason_whatsapp = reason_for

    def __init__(self, user_notification: UserNotification) -> None:
        self.user_notification = user_notification
        self.notification = user_notification.notification
        self.document = (
            user_notification.notification.document.access_for(
                actor=self.user_notification.user
            )
            if user_notification.notification.document is not None
            else None
        )
        self.fragment = (
            user_notification.notification.fragment.access_for(
                actor=self.user_notification.user
            )
            if user_notification.notification.fragment is not None
            else None
        )
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

    def tracking_tags(self, transport=None, campaign=None):
        tags = {
            # Tracking notifications unless it's unsubscribe or other specialized link
            'utm_campaign': campaign or 'notification',
            # Tracking is mostly an email thing
            'utm_medium': transport or 'email',
        }
        if not self.notification.for_private_recipient:
            tags['utm_source'] = self.notification.eventid_b58
        return tags

    def unsubscribe_token(self, transport):
        """
        Return a token suitable for use in an unsubscribe link.

        The token contains:

        1. The user id (``user.buid`` for now)
        2. The notification type (for ``user.notification_preferences``)
        3. The transport (for attribute to unset), and
        4. The transport hash, for identifying the source.

        Since tokens are sensitive, the view will strip them out of the URL before
        rendering the page, using a similar mechanism to that used for password reset.
        """
        # This payload is consumed by :meth:`AccountNotificationView.unsubscribe`
        # in `views/notification_preferences.py`
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
            **self.tracking_tags(transport=transport, campaign='unsubscribe'),
        )

    @cached_property
    def unsubscribe_url_email(self):
        return self.unsubscribe_url('email')

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
                'eventid_b58': self.notification.eventid_b58,
                'timestamp': datetime.utcnow(),  # Naive timestamp
            },
            timeout=14 * 24 * 60 * 60,  # Reserve generated token for 14 days
        )
        unsubscribe_domain = app.config.get('UNSUBSCRIBE_DOMAIN')
        if unsubscribe_domain:
            # For this to work, a web server must listen on the unsubscribe domain and
            # redirect all paths to url_for('notification_unsubscribe_short') + path
            return f'https://{unsubscribe_domain}/{token}'
        return url_for('notification_unsubscribe_short', token=token, _external=True)

    @cached_property
    def fragments_order_by(self):
        """Provide a list of order_by columns for loading fragments."""
        return [
            self.notification.fragment_model.updated_at.desc()
            if hasattr(self.notification.fragment_model, 'updated_at')
            else self.notification.fragment_model.created_at.desc()
        ]

    @property
    def fragments_query_options(self):
        """Provide a list of SQLAlchemy options for loading fragments."""
        return []

    @cached_property
    def fragments(self):
        if not self.notification.fragment_model:
            return []

        query = self.user_notification.rolledup_fragments().order_by(
            *self.fragments_order_by
        )
        if self.fragments_query_options:
            query = query.options(*self.fragments_query_options)

        return [_f.access_for(actor=self.user_notification.user) for _f in query.all()]

    @cached_property
    def is_rollup(self):
        return len(self.fragments) > 1

    def has_current_access(self) -> bool:
        return (
            self.user_notification.role
            in self.notification.role_provider_obj.current_roles
        )

    # --- Overrideable render methods

    @property
    def actor(self):
        """Actor that prompted this notification. May be overriden."""
        return self.notification.user

    def web(self) -> str:
        """
        Render for display on the website.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `web`")

    def email_subject(self) -> str:
        """
        Render the subject of an email update, suitable for handing over to send_email.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `email_subject`")

    def email_content(self) -> str:
        """
        Render an email update, suitable for handing over to send_email.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `email_content`")

    def email_attachments(self) -> Optional[List[email.EmailAttachment]]:
        """Render optional attachments to an email notification."""
        return None

    def email_from(self) -> str:
        """Sender of an email."""
        # FIXME: This field is NOT localized as it's causing an unknown downstream
        # issue that renders the From name as `=?utf-8?b?Tm90a...`
        if self.notification.preference_context:
            return f"{self.notification.preference_context.title} (via Hasgeek)"
        return "Hasgeek"

    def sms(self) -> SmsTemplate:
        """
        Render a short text message. Templates must use a single line with a link.

        Subclasses MUST implement this.
        """
        raise NotImplementedError("Subclasses must implement `sms`")

    def text(self) -> str:
        """Render a short plain text notification using the SMS template."""
        return self.sms().text

    def sms_with_unsubscribe(self) -> SmsTemplate:
        """Add an unsubscribe link to the SMS message."""
        msg = self.sms()
        msg.unsubscribe_url = self.unsubscribe_short_url('sms')
        return msg

    def webpush(self) -> str:
        """
        Render a web push notification.

        Default implementation uses :meth:`text`.
        """
        return self.text()

    def telegram(self) -> str:
        """
        Render a Telegram HTML message.

        Default implementation uses :meth:`text`.
        """
        return self.text()

    def whatsapp(self) -> str:
        """
        Render a WhatsApp-formatted text message.

        Default implementation uses :meth:`text`.
        """
        return self.text()


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
    Dispatch one or more notifications.

    Usage::

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
        if not notification.active:
            raise TypeError(f"{notification!r} is marked inactive")
        notification.eventid = eventid
        notification.user = current_auth.user
    if sum(_n.for_private_recipient for _n in notifications) not in (
        0,  # None are private
        len(notifications),  # Or all are private
    ):
        raise TypeError(
            "Mixed use of private and non-private notifications."
            " Either all are private (no event tracking in links) or none are"
        )
    db.session.add_all(notifications)
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
    """Create working context for a notification transport dispatch worker."""

    @wraps(func)
    def inner(user_notification_ids):
        """Convert a notification id into an object for worker to process."""
        queue = [
            UserNotification.query.get(identity) for identity in user_notification_ids
        ]
        for user_notification in queue:
            # The notification may be revoked by the time this worker processes it.
            # If so, skip it.
            if not user_notification.is_revoked:
                with force_locale(user_notification.user.locale or 'en'):
                    view = user_notification.views.render
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


@rqjob()
@transport_worker_wrapper
def dispatch_transport_email(
    user_notification: UserNotification, view: RenderNotification
):
    """Deliver a user notification over email."""
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
        from_email=(view.email_from(), 'no-reply@' + app.config['DEFAULT_DOMAIN']),
        headers={
            'List-Id': formataddr(
                (
                    # formataddr can't handle lazy_gettext strings, so cast to regular
                    str(user_notification.notification.title),
                    # pylint: disable=consider-using-f-string
                    '{type}-notification.{domain}'.format(
                        type=user_notification.notification.type,
                        domain=app.config['DEFAULT_DOMAIN'],
                    ),
                    # pylint: enable=consider-using-f-string
                )
            ),
            'List-Help': f'<{url_for("notification_preferences")}>',
            'List-Unsubscribe': f'<{view.unsubscribe_url_email}>',
            'List-Unsubscribe-Post': 'One-Click',
            'List-Archive': f'<{url_for("notifications")}>',
        },
    )
    statsd.incr(
        'notification.transport',
        tags={
            'notification_type': user_notification.notification_type,
            'transport': 'email',
        },
    )


@rqjob()
@transport_worker_wrapper
def dispatch_transport_sms(user_notification, view):
    """Deliver a user notification over SMS."""
    if not user_notification.user.main_notification_preferences.by_transport('sms'):
        # Cancel delivery if user's main switch is off. This was already checked, but
        # the worker may be delayed and the user may have changed their preference.
        user_notification.messageid_sms = 'cancelled'
        return
    user_notification.messageid_sms = sms.send(
        str(view.transport_for('sms')), view.sms_with_unsubscribe()
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


@rqjob()
def dispatch_notification_job(eventid, notification_ids):
    """Process :class:`Notification` into batches of :class:`UserNotification`."""
    notifications = [Notification.query.get((eventid, nid)) for nid in notification_ids]

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

    # How does this batching work? There is a confusing recipe in the itertools module
    # documentation. Here is what happens:
    #
    # `notification.dispatch()` returns a generator. We make a list of the desired batch
    # size containing repeated references to the same generator. This works because
    # Python lists can contain the same item multiple times, and ``[item] * 2 == [item,
    # item]`` (also: ``[1, 2] * 2 = [1, 2, 1, 2]``). These copies are fed as positional
    # parameters to `zip_longest`, which returns a batch containing one item from each
    # of its parameters. For each batch (size 10 from the constant defined above), we
    # commit to database and then queue a background job to deliver to them. When
    # `zip_longest` runs out of items, it returns a batch padded with the `fillvalue`
    # None. We use `filterfalse` to discard these None values. This difference
    # distinguishes `zip_longest` from `zip`, which truncates the source data when it is
    # short of a full batch.
    #
    # Discussion of approaches at https://stackoverflow.com/q/8290397/78903


@rqjob()
def dispatch_user_notifications_job(user_notification_ids):
    """Process notifications for users and enqueue transport delivery."""
    queue = [UserNotification.query.get(identity) for identity in user_notification_ids]
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
