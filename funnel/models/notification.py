"""
Notification primitives.

Notification models and support classes for implementing notifications, best understood
using examples:

Scenario: Project P's editor E posts an update U
Where: User A is a participant on the project
Result: User A receives a notification about a new update on the project

How it works:

1. View handler that creates the Update triggers an UpdateNotification on it. This is
    a subclass of Notification. The UpdateNotification class specifies the roles that
    must receive the notification.

2. Roles? Yes. UpdateNotification says it should be delivered to users possessing the
    roles 'project_crew' and 'project_participant' on the Update object, in that order.
    That means a user who is both crew and participant will only get the version meant
    for crew members and won't be notified twice. Versions will have minor differences
    such as in language: "the project you're a crew member of had an update", versus
    "the project you're a participant of had an update".

3. An UpdateNotification instance (a polymorphic class on top of Notification) is
    created referring to the Update instance. It is then dispatched from the view by
    calling the dispatch method on it, an iterator. This returns UserNotification
    instances.

4. To find users with the required roles, `Update.actors_for({roles})` is called. The
    default implementation in RoleMixin is aware that these roles are inherited from
    Project (using granted_via declarations), and so calls `Update.project.actors_for`.

5. UserNotification.dispatch is now called from the view. User preferences are obtained
    from the User model along with transport address (email, phone, etc).

6. For each user in the filtered list, a UserNotification db instance is created.

7. For notifications (not this one) where both a document and a fragment are present,
    like ProposalReceivedNotication with Project+Proposal, a scan is performed for
    previous unread instances of UserNotification referring to the same document,
    determined from UserNotification.notification.document_uuid, and those are revoked
    to remove them from the user's feed. A rollup is presented instead, showing all
    freshly submitted proposals.

8. A separate render view class named RenderNewUpdateNotification contains methods named
    like `web`, `email`, `sms` and others. These are expected to return a rendered
    message. The `web` render is used for the notification feed page on the website.

9. Views are registered to the model, so the dispatch mechanism only needs to call
    ``view.email()`` etc to get the rendered content. The dispatch mechanism then calls
    the appropriate transport helper (``send_email``, etc) to do the actual sending. The
    message id returned by these functions is saved to the messageid columns in
    UserNotification, as record that the notification was sent. If the transport doesn't
    support message ids, a random non-None value is used. Accurate message ids are only
    required when user interaction over the same transport is expected, such as reply
    emails.

10. The notifications endpoint on the website shows a feed of UserNotification items and
    handles the ability to mark each as read. This marking is not yet automatically
    performed in the links in the rendered templates that were sent out, but should be.

It is possible to have two separate notifications for the same event. For example, a
comment replying to another comment will trigger a CommentReplyNotification to the user
being replied to, and a ProjectCommentNotification or ProposalCommentNotification for
the project or proposal. The same user may be a recipient of both notifications. To
de-duplicate this, a random "eventid" is shared across both notifications, and is
required to be unique per user, so that the second notification will be skipped. This
is supported using an unusual primary and foreign key structure the in
:class:`Notification` and :class:`UserNotification`:

1. Notification has pkey ``(eventid, id)``, where `id` is local to the instance
2. UserNotification has pkey ``(eventid, user_id)`` combined with a fkey to Notification
    using ``(eventid, notification_id)``.
"""
from types import SimpleNamespace
from typing import Callable, NamedTuple
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.collections import column_mapped_collection

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import auto_init_default, with_roles
from coaster.utils import LabeledEnum, classmethodproperty

from . import BaseMixin, NoIdMixin, UUIDType, db
from .helpers import reopen
from .user import User

__all__ = [
    'SMS_STATUS',
    'notification_categories',
    'SMSMessage',
    'Notification',
    'PreviewNotification',
    'NotificationPreferences',
    'UserNotification',
    'NotificationFor',
    'notification_type_registry',
]

# --- Registries -----------------------------------------------------------------------

#: Registry of Notification subclasses, automatically populated
notification_type_registry = {}


class NotificationCategory(NamedTuple):
    priority_id: int
    title: str
    available_for: Callable[[User], bool]


#: Registry of notification categories
notification_categories = SimpleNamespace(
    none=NotificationCategory(0, __("Uncategorized"), lambda user: False),
    account=NotificationCategory(1, __("My account"), lambda user: True),
    subscriptions=NotificationCategory(
        2, __("My subscriptions and billing"), lambda user: False
    ),
    participant=NotificationCategory(
        3,
        __("Projects I am participating in"),
        # Criteria: User has registered or proposed
        lambda user: (
            db.session.query(user.rsvps.exists()).scalar()
            or db.session.query(user.proposals.exists()).scalar()
            or db.session.query(user.speaker_at.exists()).scalar()
            or db.session.query(user.proposal_memberships.exists()).scalar()
        ),
    ),
    project_crew=NotificationCategory(
        4,
        __("Projects I am a crew member in"),
        # Criteria: user has ever been a project crew member
        lambda user: db.session.query(
            user.projects_as_crew_memberships.exists()
        ).scalar(),
    ),
    organization_admin=NotificationCategory(
        5,
        __("Organizations I manage"),
        # Criteria: user has ever been an organization admin
        lambda user: db.session.query(
            user.organization_admin_memberships.exists()
        ).scalar(),
    ),
    site_admin=NotificationCategory(
        6,
        __("As a website administrator"),
        # Criteria: User has a currently active site membership
        lambda user: bool(user.active_site_membership),
    ),
)


# --- Flags ----------------------------------------------------------------------------


class SMS_STATUS(LabeledEnum):  # NOQA: N801
    QUEUED = (0, __("Queued"))
    PENDING = (1, __("Pending"))
    DELIVERED = (2, __("Delivered"))
    FAILED = (3, __("Failed"))
    UNKNOWN = (4, __("Unknown"))


# --- Legacy models --------------------------------------------------------------------


class SMSMessage(BaseMixin, db.Model):
    __tablename__ = 'sms_message'
    # Phone number that the message was sent to
    phone_number = db.Column(db.String(15), nullable=False)
    transactionid = db.Column(db.UnicodeText, unique=True, nullable=True)
    # The message itself
    message = db.Column(db.UnicodeText, nullable=False)
    # Flags
    status = db.Column(db.Integer, default=SMS_STATUS.QUEUED, nullable=False)
    status_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    fail_reason = db.Column(db.UnicodeText, nullable=True)


# -- Notification models ---------------------------------------------------------------


class Notification(NoIdMixin, db.Model):
    """
    Holds a single notification for an activity on a document object.

    Notifications are fanned out to recipients using :class:`UserNotification` and
    may be accessed through the website and delivered over email, push notification, SMS
    or other transport.

    Notifications cannot hold any data and must source everything from the linked
    document and fragment.
    """

    __tablename__ = 'notification'

    #: Flag indicating this is an active notification type. Can be False for draft
    #: and retired notification types to hide them from preferences UI
    active = True

    #: Random identifier for the event that triggered this notification. Event ids can
    #: be shared across notifications, and will be used to enforce a limit of one
    #: instance of a UserNotification per-event rather than per-notification
    eventid = db.Column(
        UUIDType(binary=False), primary_key=True, nullable=False, default=uuid4
    )

    #: Notification id
    id = db.Column(  # NOQA: A003
        UUIDType(binary=False), primary_key=True, nullable=False, default=uuid4
    )

    #: Default category of notification. Subclasses MUST override
    category = notification_categories.none
    #: Default description for notification. Subclasses MUST override
    title = __("Unspecified notification type")
    #: Default description for notification. Subclasses MUST override
    description = ''

    #: Subclasses may set this to aid loading of :attr:`document`
    document_model = None

    #: Subclasses may set this to aid loading of :attr:`fragment`
    fragment_model = None

    #: Roles to send notifications to. Roles must be in order of priority for situations
    #: where a user has more than one role on the document.
    roles = []

    #: Exclude triggering actor from receiving notifications? Subclasses may override
    exclude_actor = False

    #: If this notification is typically for a single recipient, views will need to be
    #: careful about leaking out recipient identifiers such as a utm_source tracking tag
    for_private_recipient = False

    #: The preference context this notification is being served under. Users may have
    #: customized preferences per profile or project
    preference_context = None

    #: Notification type (identifier for subclass of :class:`NotificationType`)
    type = db.Column(db.Unicode, nullable=False)  # NOQA: A003

    #: Id of user that triggered this notification
    user_id = db.Column(
        None, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    #: User that triggered this notification. Optional, as not all notifications are
    #: caused by user activity. Used to optionally exclude user from receiving
    #: notifications of their own activity
    user = db.relationship(User)

    #: UUID of document that the notification refers to
    document_uuid = db.Column(UUIDType(binary=False), nullable=False, index=True)

    #: Optional fragment within document that the notification refers to. This may be
    #: the document itself, or something within it, such as a comment. Notifications for
    #: multiple fragments are collapsed into a single notification
    fragment_uuid = db.Column(UUIDType(binary=False), nullable=True)

    __table_args__ = (
        # This could have been achieved with a UniqueConstraint on all three columns.
        # When the third column (fragment_uuid) is null it has the same effect as the
        # PostgreSQL-specific where clause. We use the clause here to make clear our
        # intent of only enforcing a one-notification limit when the fragment is
        # present. Hence the naming convention of `_key` suffix rather than `ix_` prefix
        db.Index(
            'notification_type_document_uuid_fragment_uuid_key',
            type,
            document_uuid,
            fragment_uuid,
            unique=True,
            postgresql_where=fragment_uuid.isnot(None),
        ),
    )

    __mapper_args__ = {
        # 'polymorphic_identity' from subclasses is stored in the type column
        'polymorphic_on': type,
        # When querying the Notification model, cast automatically to all subclasses
        'with_polymorphic': '*',
    }

    __datasets__ = {
        'primary': {'eventid', 'document', 'fragment', 'type', 'user'},
        'related': {'eventid', 'document', 'fragment', 'type'},
    }

    # Flags to control whether this notification can be delivered over a particular
    # transport. Subclasses can disable these if they consider notifications unsuitable
    # for particular transports.

    #: This notification class may be seen on the website
    allow_web = True
    #: This notification class may be delivered by email
    allow_email = True
    #: This notification class may be delivered by SMS
    allow_sms = True
    #: This notification class may be delivered by push notification
    allow_webpush = True
    #: This notification class may be delivered by Telegram message
    allow_telegram = True
    #: This notification class may be delivered by WhatsApp message
    allow_whatsapp = True

    # Flags to set defaults for transports, in case the user has not made a choice

    #: By default, turn on/off delivery by email
    default_email = True
    #: By default, turn on/off delivery by SMS
    default_sms = True
    #: By default, turn on/off delivery by push notification
    default_webpush = True
    #: By default, turn on/off delivery by Telegram message
    default_telegram = True
    #: By default, turn on/off delivery by WhatsApp message
    default_whatsapp = True

    #: Ignore transport errors? If True, an error will be ignored silently. If False,
    #: an error report will be logged for the user or site administrator. TODO
    ignore_transport_errors = False

    #: Registry of per-class renderers
    renderers = {}  # Registry of {cls_type: CustomNotificationView}

    def __init__(self, document=None, fragment=None, **kwargs):
        if document:
            if not isinstance(document, self.document_model):
                raise TypeError(f"{document!r} is not of type {self.document_model!r}")
            kwargs['document_uuid'] = document.uuid
        if fragment:
            if not isinstance(fragment, self.fragment_model):
                raise TypeError(f"{fragment!r} is not of type {self.fragment_model!r}")
            kwargs['fragment_uuid'] = fragment.uuid
        super().__init__(**kwargs)

    @classmethodproperty
    def cls_type(cls):  # NOQA: N805
        return cls.__mapper_args__['polymorphic_identity']

    @property
    def identity(self):
        """Primary key of this object."""
        return (self.eventid, self.id)

    @cached_property
    def document(self):
        """
        Retrieve the document referenced by this Notification, if any.

        This assumes the underlying object won't disappear, as there is no SQL foreign
        key constraint enforcing a link. The proper way to do this is by having a
        secondary table for each type of document.
        """
        if self.document_model and self.document_uuid:
            return self.document_model.query.filter_by(uuid=self.document_uuid).one()
        return None

    @cached_property
    def fragment(self):
        """
        Retrieve the fragment within a document referenced by this Notification, if any.

        This assumes the underlying object won't disappear, as there is no SQL foreign
        key constraint enforcing a link.
        """
        if self.fragment_model and self.fragment_uuid:
            return self.fragment_model.query.filter_by(uuid=self.fragment_uuid).one()
        return None

    @classmethod
    def renderer(cls, view):
        """
        Decorator for view class containing render methods.

        Usage in views::

            from ..models import MyNotificationType
            from .views import NotificationView

            @MyNotificationType.renderer
            class MyNotificationView(NotificationView):
                ...
        """
        if cls.cls_type in cls.renderers:
            raise TypeError(
                f"A renderer has already been registered for {cls.cls_type}"
            )
        cls.renderers[cls.cls_type] = view
        return view

    @classmethod
    def allow_transport(cls, transport):
        """Helper method to return ``cls.allow_<transport>``."""
        return getattr(cls, 'allow_' + transport)

    def dispatch(self):
        """
        Create :class:`UserNotification` instances and yield in an iterator.

        This is a heavy method and must be called from a background job. When making
        new notifications, it will revoke previous notifications issued against the
        same document.

        Subclasses wanting more control over how their notifications are dispatched
        should override this method.
        """
        for user, role in (self.fragment or self.document).actors_with(
            self.roles, with_role=True
        ):
            # If this notification requires that it not be sent to the actor that
            # triggered the notification, don't notify them. For example, a user
            # who leaves a comment should not be notified of their own comment.
            # This `if` condition uses `user_id` instead of the recommended `user`
            # for faster processing in a loop.
            if (
                self.exclude_actor
                and self.user_id is not None
                and self.user_id == user.id
            ):
                continue

            # Don't notify inactive (suspended, merged) users
            if not user.is_active:
                continue

            # Was a notification already sent to this user? If so:
            # 1. The user has multiple roles
            # 2. We're being dispatched a second time, possibly because a background
            #    job failed and is re-queued.
            # In either case, don't notify the user a second time.

            # Since this query uses SQLAlchemy's session cache, we don't have to
            # bother with a local cache for the first case.
            existing_notification = UserNotification.query.get((user.id, self.eventid))
            if not existing_notification:
                user_notification = UserNotification(
                    eventid=self.eventid,
                    user_id=user.id,
                    notification_id=self.id,
                    role=role,
                )
                db.session.add(user_notification)
                yield user_notification


class PreviewNotification:
    """
    Mimics a Notification subclass without instantiating it, for providing a preview.

    To be used with :class:`NotificationFor`::

        NotificationFor(PreviewNotification(NotificationType), user)
    """

    def __init__(self, cls, document, fragment=None):
        self.eventid = self.id = 'preview'  # May need to be a UUID
        self.cls = cls
        self.document = document
        self.document_uuid = document.uuid
        self.fragment = fragment
        self.fragment_uuid = fragment.uuid

    def __getattr__(self, attr):
        return getattr(self.cls, attr)


class UserNotificationMixin:
    """
    Contains helper methods for :class:`UserNotification` and :class:`NotificationFor`.
    """

    @with_roles(read={'owner'})
    @property
    def notification_type(self):
        return self.notification.type

    @with_roles(read={'owner'})
    @property
    def document_type(self):
        return (
            self.notification.document_model.__tablename__
            if self.notification.document_model
            else None
        )

    @with_roles(read={'owner'})
    @property
    def document(self):
        """The document that this notification is for."""
        return self.notification.document

    @with_roles(read={'owner'})
    @property
    def fragment_type(self):
        return (
            self.notification.fragment_model.__tablename__
            if self.notification.fragment_model
            else None
        )

    @with_roles(read={'owner'})
    @property
    def fragment(self):
        """The fragment within this document that this notification is for."""
        return self.notification.fragment


class UserNotification(UserNotificationMixin, NoIdMixin, db.Model):
    """
    The recipient of a notification.

    Contains delivery metadata and helper methods to render the notification.
    """

    __tablename__ = 'user_notification'

    # Primary key is a compound of (user_id, eventid).

    #: Id of user being notified
    user_id = db.Column(
        None,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    #: User being notified (backref defined below, outside the model)
    user = with_roles(db.relationship(User), read={'owner'}, grants={'owner'})

    #: Random eventid, shared with the Notification instance
    eventid = with_roles(
        db.Column(UUIDType(binary=False), primary_key=True, nullable=False),
        read={'owner'},
    )

    #: Id of notification that this user received
    notification_id = db.Column(None, nullable=False)  # fkey in __table_args__ below
    #: Notification that this user received
    notification = with_roles(
        db.relationship(Notification, backref=db.backref('recipients', lazy='dynamic')),
        read={'owner'},
    )

    #: The role they held at the time of receiving the notification, used for
    #: customizing the template.
    #:
    #: Note: This column represents the first instance of a role shifting from being an
    #: entirely in-app symbol (i.e., code refactorable) to being data in the database
    #: (i.e., requiring a data migration alongside a code refactor)
    role = with_roles(db.Column(db.Unicode, nullable=False), read={'owner'})

    #: Timestamp for when this notification was marked as read
    read_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), default=None, nullable=True),
        read={'owner'},
    )

    #: Whether the notification has been revoked. This can happen if:
    #: 1. The action that caused the notification has been undone (future use), or
    #: 2. A new notification has been raised for the same document and this user was
    #:    a recipient of the new notification.
    is_revoked = with_roles(
        db.Column(db.Boolean, default=False, nullable=False, index=True), read={'owner'}
    )

    #: When a roll-up is performed, record an identifier for the items rolled up
    rollupid = with_roles(
        db.Column(UUIDType(binary=False), nullable=True, index=True), read={'owner'}
    )

    #: Message id for email delivery
    messageid_email = db.Column(db.Unicode, nullable=True)
    #: Message id for SMS delivery
    messageid_sms = db.Column(db.Unicode, nullable=True)
    #: Message id for web push delivery
    messageid_webpush = db.Column(db.Unicode, nullable=True)
    #: Message id for Telegram delivery
    messageid_telegram = db.Column(db.Unicode, nullable=True)
    #: Message id for WhatsApp delivery
    messageid_whatsapp = db.Column(db.Unicode, nullable=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [eventid, notification_id],
            [Notification.eventid, Notification.id],
            ondelete='CASCADE',
            name='user_notification_eventid_notification_id_fkey',
        ),
    )

    __roles__ = {'owner': {'read': {'created_at'}}}

    __datasets__ = {
        'primary': {
            'created_at',
            'eventid',
            'role',
            'read_at',
            'is_read',
            'is_revoked',
            'rollupid',
            'notification_type',
            'document_type',
            'fragment_type',
        },
        'related': {
            'created_at',
            'eventid',
            'role',
            'read_at',
            'is_read',
            'is_revoked',
            'rollupid',
        },
    }

    # --- User notification properties -------------------------------------------------

    @property
    def identity(self):
        """Primary key of this object."""
        return (self.user_id, self.eventid)

    @hybrid_property
    def is_read(self):
        """Whether this notification has been marked as read."""
        return self.read_at is not None

    @is_read.setter
    def is_read(self, value):
        if value:
            if not self.read_at:
                self.read_at = db.func.utcnow()
        else:
            self.read_at = None

    @is_read.expression
    def is_read(cls):  # NOQA: N805
        return cls.read_at.isnot(None)

    with_roles(is_read, rw={'owner'})

    # --- Dispatch helper methods ------------------------------------------------------

    def user_preferences(self):
        """Return the user's notification preferences for this notification type."""
        prefs = self.user.notification_preferences.get(self.notification_type)
        if not prefs:
            prefs = NotificationPreferences(
                user=self.user, notification_type=self.notification_type
            )
            db.session.add(prefs)
            self.user.notification_preferences[self.notification_type] = prefs
        return prefs

    def has_transport(self, transport):
        """
        Return whether the requested transport is an option.

        Uses four criteria:

        1. The notification type allows delivery over this transport
        2. The user's main transport preferences allow this one
        3. The user's per-type preference allows it
        4. The user actually has this transport (verified email or phone, etc)
        """
        # This property inserts the row if not already present. An immediate database
        # commit is required to ensure a parallel worker processing another notification
        # doesn't make a conflicting row.
        main_prefs = self.user.main_notification_preferences
        user_prefs = self.user_preferences()
        return (
            self.notification.allow_transport(transport)
            and main_prefs.by_transport(transport)
            and user_prefs.by_transport(transport)
            and self.user.has_transport(transport)
        )

    def transport_for(self, transport):
        """
        Return transport address for the requested transport.

        Uses four criteria:

        1. The notification type allows delivery over this transport
        2. The user's main transport preferences allow this one
        3. The user's per-type preference allows it
        4. The user has this transport (verified email or phone, etc)
        """
        main_prefs = self.user.main_notification_preferences
        user_prefs = self.user_preferences()
        if (
            self.notification.allow_transport(transport)
            and main_prefs.by_transport(transport)
            and user_prefs.by_transport(transport)
        ):
            return self.user.transport_for(
                transport, self.notification.preference_context
            )
        return None

    def rollup_previous(self):
        """
        Rollup prior instances of :class:`UserNotification` against the same document.

        Revokes and sets a shared rollup id on all prior user notifications.
        """
        if not self.notification.fragment_model:
            # We can only rollup fragments within a document. Rollup doesn't apply
            # for notifications without fragments.
            return

        if self.is_revoked or self.rollupid is not None:
            # We've already been revoked or rolled up. Nothing to do.
            return

        # For rollup: find most recent unread that has a rollupid. Reuse that id so that
        # the current notification becomes the latest in that batch of rolled up
        # notifications. If none, this is the start of a new batch, so make a new id.
        rollupid = (
            db.session.query(UserNotification.rollupid)
            .join(Notification)
            .filter(
                # Same user
                UserNotification.user_id == self.user_id,
                # Same type of notification
                Notification.type == self.notification.type,
                # Same document
                Notification.document_uuid == self.notification.document_uuid,
                # Same reason for receiving notification as earlier instance (same role)
                UserNotification.role == self.role,
                # Earlier instance is unread
                UserNotification.read_at.is_(None),
                # Earlier instance is not revoked
                UserNotification.is_revoked.is_(False),
                # Earlier instance has a rollupid
                UserNotification.rollupid.isnot(None),
            )
            .order_by(UserNotification.created_at.asc())
            .limit(1)
            .scalar()
        )
        if not rollupid:
            # No previous rollupid? Then we're the first. The next notification
            # will use our rollupid as long as we're unread
            self.rollupid = uuid4()
        else:
            # Use the existing id, find all using it and revoke them
            self.rollupid = rollupid

            # Now rollup all previous unread. This will skip (a) previously revoked user
            # notifications, and (b) unrolled but read user notifications.
            for previous in (
                UserNotification.query.join(Notification)
                .filter(
                    # Same user
                    UserNotification.user_id == self.user_id,
                    # Not ourselves
                    UserNotification.eventid != self.eventid,
                    # Same type of notification
                    Notification.type == self.notification.type,
                    # Same document
                    Notification.document_uuid == self.notification.document_uuid,
                    # Same role as earlier notification,
                    UserNotification.role == self.role,
                    # Earlier instance is not revoked
                    UserNotification.is_revoked.is_(False),
                    # Earlier instance shares our rollupid
                    UserNotification.rollupid == self.rollupid,
                )
                .options(
                    db.load_only(
                        UserNotification.user_id,
                        UserNotification.eventid,
                        UserNotification.is_revoked,
                        UserNotification.rollupid,
                    )
                )
            ):
                previous.is_revoked = True
                previous.rollupid = self.rollupid

    def rolledup_fragments(self):
        """Return all fragments in the rolled up batch as a base query."""
        if not self.notification.fragment_model:
            return None
        # Return a query
        if not self.rollupid:
            return self.notification.fragment_model.query.filter_by(
                uuid=self.notification.fragment_uuid
            )
        return self.notification.fragment_model.query.filter(
            self.notification.fragment_model.uuid.in_(
                db.session.query(Notification.fragment_uuid)
                .select_from(UserNotification)
                .join(UserNotification.notification)
                .filter(UserNotification.rollupid == self.rollupid)
            )
        )

    @classmethod
    def migrate_user(cls, old_user, new_user):
        for user_notification in cls.query.filter_by(user_id=old_user.id).all():
            existing = cls.query.get((new_user.id, user_notification.eventid))
            # TODO: Instead of dropping old_user's dupe notifications, check which of
            # the two has a higher priority role and keep that. This may not be possible
            # if the two copies are for different notifications under the same eventid.
            if existing:
                db.session.delete(user_notification)
            else:
                user_notification.user_id = new_user.id


class NotificationFor(UserNotificationMixin):
    """View-only wrapper to mimic :class:`UserNotification`."""

    identity = read_at = None
    is_revoked = is_read = False

    def __init__(self, notification, user):
        self.notification = notification
        self.eventid = notification.eventid
        self.notification_id = notification.id

        self.user = user
        self.user_id = user.id

    @property
    def role(self):
        """User's primary matching role for this notification."""
        if self.document and self.user:
            roles = self.document.roles_for(self.user)
            for role in self.notification.roles:
                if role in roles:
                    return role
        return None

    def rolledup_fragments(self):
        if not self.notification.fragment_model:
            return None
        return [self.fragment]


# --- Notification preferences ---------------------------------------------------------


class NotificationPreferences(BaseMixin, db.Model):
    """Holds a user's preferences for a particular Notification type"""

    __tablename__ = 'notification_preferences'

    #: Id of user whose preferences are represented here
    user_id = db.Column(
        None, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True,
    )
    #: User whose preferences are represented here
    user = with_roles(db.relationship(User), read={'owner'}, grants={'owner'},)

    # Notification type, corresponding to Notification.type (a class attribute there)
    # notification_type = '' holds the veto switch to disable a transport entirely
    notification_type = db.Column(db.Unicode, nullable=False)

    by_email = with_roles(db.Column(db.Boolean, nullable=False), rw={'owner'})
    by_sms = with_roles(db.Column(db.Boolean, nullable=False), rw={'owner'})
    by_webpush = with_roles(db.Column(db.Boolean, nullable=False), rw={'owner'})
    by_telegram = with_roles(db.Column(db.Boolean, nullable=False), rw={'owner'})
    by_whatsapp = with_roles(db.Column(db.Boolean, nullable=False), rw={'owner'})

    __table_args__ = (db.UniqueConstraint('user_id', 'notification_type'),)

    __datasets__ = {
        'preferences': {
            'by_email',
            'by_sms',
            'by_webpush',
            'by_telegram',
            'by_whatsapp',
        }
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.user:
            self.set_defaults()

    def __repr__(self):
        return (
            f'NotificationPreferences('
            f'notification_type={self.notification_type!r}, user={self.user!r}'
            f')'
        )

    def set_defaults(self):
        """
        Set defaults based on notification type's defaults, and previous user prefs.
        """
        transport_attrs = (
            ('by_email', 'default_email'),
            ('by_sms', 'default_sms'),
            ('by_webpush', 'default_webpush'),
            ('by_telegram', 'default_telegram'),
            ('by_whatsapp', 'default_whatsapp'),
        )
        if not self.user.notification_preferences:
            # No existing preferences. Get defaults from notification type's class
            if (
                self.notification_type
                and self.notification_type in notification_type_registry
            ):
                type_cls = notification_type_registry[self.notification_type]
                for t_attr, d_attr in transport_attrs:
                    if getattr(self, t_attr) is None:
                        setattr(self, t_attr, getattr(type_cls, d_attr))
            else:
                # No notification type class either. Turn on everything.
                for t_attr, d_attr in transport_attrs:
                    if getattr(self, t_attr) is None:
                        setattr(self, t_attr, True)
        else:
            for t_attr, d_attr in transport_attrs:
                if getattr(self, t_attr) is None:
                    # If this transport is enabled for any existing notification type,
                    # also enable here.
                    setattr(
                        self,
                        t_attr,
                        any(
                            getattr(np, t_attr)
                            for np in self.user.notification_preferences.values()
                        ),
                    )

    @with_roles(call={'owner'})
    def by_transport(self, transport):
        """Helper method to return ``self.by_<transport>``."""
        return getattr(self, 'by_' + transport)

    @with_roles(call={'owner'})
    def set_transport(self, transport, value):
        """Helper method to set a preference for a transport."""
        setattr(self, 'by_' + transport, value)

    @cached_property
    def type_cls(self):
        """Return the Notification subclass corresponding to self.notification_type"""
        # Use `registry.get(type)` instead of `registry[type]` because the user may have
        # saved preferences for a discontinued notification type. These should ideally
        # be dropped in migrations, but it's possible for the data to be outdated.
        return notification_type_registry.get(self.notification_type)

    @classmethod
    def migrate_user(cls, old_user, new_user):
        for ntype, prefs in list(old_user.notification_preferences.items()):
            if ntype not in new_user.notification_preferences:
                prefs.user = new_user
            else:
                db.session.delete(prefs)

    @db.validates('notification_type')
    def _valid_notification_type(self, key, value):
        if value == '':  # Special-cased name for main preferences
            return value
        if value is None or value not in notification_type_registry:
            raise ValueError("Invalid notification_type: %s" % value)
        return value


@reopen(User)
class User:
    all_notifications = with_roles(
        db.relationship(
            UserNotification,
            lazy='dynamic',
            order_by=UserNotification.created_at.desc(),
        ),
        read={'owner'},
    )

    notification_preferences = db.relationship(
        NotificationPreferences,
        collection_class=column_mapped_collection(
            NotificationPreferences.notification_type
        ),
    )

    # This relationship is wrapped in a property that creates it on first access
    _main_notification_preferences = db.relationship(
        NotificationPreferences,
        primaryjoin=db.and_(
            NotificationPreferences.user_id == User.id,
            NotificationPreferences.notification_type == '',
        ),
        uselist=False,
    )

    @property
    def main_notification_preferences(self):
        if not self._main_notification_preferences:
            self._main_notification_preferences = NotificationPreferences(
                user=self,
                notification_type='',
                by_email=True,
                by_sms=False,
                by_webpush=False,
                by_telegram=False,
                by_whatsapp=False,
            )
            db.session.add(self._main_notification_preferences)
        return self._main_notification_preferences


# --- Signal handlers ------------------------------------------------------------------


auto_init_default(Notification.eventid)


@event.listens_for(Notification, 'mapper_configured', propagate=True)
def _register_notification_types(mapper_, cls):
    # Don't register the base class itself, or inactive types
    if cls is not Notification and cls.active:
        notification_type_registry[cls.__mapper_args__['polymorphic_identity']] = cls
