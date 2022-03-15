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
from __future__ import annotations

from types import SimpleNamespace
from typing import (
    Callable,
    Dict,
    Generator,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    get_type_hints,
)
from uuid import UUID, uuid4

from sqlalchemy import event
from sqlalchemy.orm.collections import column_mapped_collection
from sqlalchemy.orm.exc import NoResultFound

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import (
    Query,
    SqlUuidB58Comparator,
    auto_init_default,
    immutable,
    with_roles,
)
from coaster.utils import LabeledEnum, uuid_from_base58, uuid_to_base58

from .. import models  # For locals() namespace, to discover models from type defn
from ..typing import OptionalMigratedTables, T
from . import BaseMixin, NoIdMixin, UuidMixin, UUIDType, db, hybrid_property
from .helpers import reopen
from .user import User, UserEmail, UserPhone

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
    'notification_web_types',
]

# --- Registries -----------------------------------------------------------------------

#: Registry of Notification subclasses, automatically populated
notification_type_registry: Dict[str, Notification] = {}
#: Registry of notification types that allow web renders
notification_web_types: Set[Notification] = set()


class NotificationCategory(NamedTuple):
    priority_id: int
    title: str
    available_for: Callable[[User], bool]


#: Registry of notification categories
notification_categories: SimpleNamespace = SimpleNamespace(
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


class SMS_STATUS(LabeledEnum):
    QUEUED = (0, __("Queued"))
    PENDING = (1, __("Pending"))
    DELIVERED = (2, __("Delivered"))
    FAILED = (3, __("Failed"))
    UNKNOWN = (4, __("Unknown"))


# --- Legacy models --------------------------------------------------------------------


class SMSMessage(BaseMixin, db.Model):
    __tablename__ = 'sms_message'
    # Phone number that the message was sent to
    phone_number = immutable(db.Column(db.String(15), nullable=False))
    transactionid = immutable(db.Column(db.UnicodeText, unique=True, nullable=True))
    # The message itself
    message = immutable(db.Column(db.UnicodeText, nullable=False))
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
    eventid = immutable(
        db.Column(
            UUIDType(binary=False), primary_key=True, nullable=False, default=uuid4
        )
    )

    #: Notification id
    id = immutable(
        db.Column(
            UUIDType(binary=False), primary_key=True, nullable=False, default=uuid4
        )
    )

    #: Default category of notification. Subclasses MUST override
    category: NotificationCategory = notification_categories.none
    #: Default description for notification. Subclasses MUST override
    title = __("Unspecified notification type")
    #: Default description for notification. Subclasses MUST override
    description = ''

    #: Subclasses must set document type to aid loading of :attr:`document`
    document: UuidMixin

    #: Subclasses must set fragment type to aid loading of :attr:`fragment`
    fragment: Optional[UuidMixin]

    #: Document model is auto-populated from the document type
    document_model: UuidMixin
    #: Document type is auto-populated from the document model
    document_type: str

    #: Fragment model is auto-populated from the fragment type
    fragment_model: Optional[UuidMixin]

    #: Fragment type is auto-populated from the fragment model
    fragment_type: Optional[str]

    #: Roles to send notifications to. Roles must be in order of priority for situations
    #: where a user has more than one role on the document.
    roles: Sequence[str] = []

    #: Exclude triggering actor from receiving notifications? Subclasses may override
    exclude_actor = False

    #: If this notification is typically for a single recipient, views will need to be
    #: careful about leaking out recipient identifiers such as a utm_source tracking tag
    for_private_recipient = False

    #: The preference context this notification is being served under. Users may have
    #: customized preferences per profile or project
    preference_context: db.Model = None

    #: Notification type (identifier for subclass of :class:`NotificationType`)
    type_ = immutable(db.Column('type', db.Unicode, nullable=False))

    #: Id of user that triggered this notification
    user_id = immutable(
        db.Column(None, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    )
    #: User that triggered this notification. Optional, as not all notifications are
    #: caused by user activity. Used to optionally exclude user from receiving
    #: notifications of their own activity
    user = immutable(db.relationship(User))

    #: UUID of document that the notification refers to
    document_uuid = immutable(
        db.Column(UUIDType(binary=False), nullable=False, index=True)
    )

    #: Optional fragment within document that the notification refers to. This may be
    #: the document itself, or something within it, such as a comment. Notifications for
    #: multiple fragments are collapsed into a single notification
    fragment_uuid = immutable(db.Column(UUIDType(binary=False), nullable=True))

    __table_args__ = (
        # This could have been achieved with a UniqueConstraint on all three columns.
        # When the third column (fragment_uuid) is null it has the same effect as the
        # PostgreSQL-specific where clause. We use the clause here to make clear our
        # intent of only enforcing a one-notification limit when the fragment is
        # present. Hence the naming convention of `_key` suffix rather than `ix_` prefix
        db.Index(
            'notification_type_document_uuid_fragment_uuid_key',
            type_,
            document_uuid,
            fragment_uuid,
            unique=True,
            postgresql_where=fragment_uuid.isnot(None),
        ),
    )

    __mapper_args__ = {
        # 'polymorphic_identity' from subclasses is stored in the type column
        'polymorphic_on': type_,
        # When querying the Notification model, cast automatically to all subclasses
        'with_polymorphic': '*',
    }

    __roles__ = {
        'all': {
            'read': {'document_type', 'fragment_type'},
        }
    }

    __datasets__ = {
        'primary': {
            'eventid',
            'eventid_b58',
            'document_type',
            'fragment_type',
            'document',
            'fragment',
            'type',
            'user',
        },
        'related': {
            'eventid',
            'eventid_b58',
            'document_type',
            'fragment_type',
            'document',
            'fragment',
            'type',
        },
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

    #: Registry of per-class renderers ``{cls_type(): CustomNotificationView}``
    renderers: Dict[str, Type] = {}  # Can't import RenderNotification from views here

    def __init__(self, document=None, fragment=None, **kwargs) -> None:
        if document is not None:
            if not isinstance(document, self.document_model):
                raise TypeError(f"{document!r} is not of type {self.document_model!r}")
            kwargs['document_uuid'] = document.uuid
        if fragment is not None:
            if self.fragment_model is None:
                raise TypeError(f"{self.__class__} is not expecting a fragment")
            if not isinstance(fragment, self.fragment_model):
                raise TypeError(f"{fragment!r} is not of type {self.fragment_model!r}")
            kwargs['fragment_uuid'] = fragment.uuid
        super().__init__(**kwargs)

    @classmethod
    def cls_type(cls) -> str:
        return cls.__mapper_args__['polymorphic_identity']

    @property
    def identity(self) -> Tuple[UUID, UUID]:
        """Primary key of this object."""
        return (self.eventid, self.id)

    @hybrid_property
    def eventid_b58(self) -> str:
        """URL-friendly UUID representation, using Base58 with the Bitcoin alphabet."""
        return uuid_to_base58(self.eventid)

    @eventid_b58.setter
    def eventid_b58(self, value: str) -> None:
        self.eventid = uuid_from_base58(value)

    @eventid_b58.comparator
    def eventid_b58(cls):
        return SqlUuidB58Comparator(cls.eventid)

    @cached_property  # type: ignore[no-redef]
    def document(self):
        """
        Retrieve the document referenced by this Notification, if any.

        This assumes the underlying object won't disappear, as there is no SQL foreign
        key constraint enforcing a link. The proper way to do this is by having a
        secondary table for each type of document.
        """
        if self.document_uuid and self.document_model:
            return self.document_model.query.filter_by(uuid=self.document_uuid).one()
        return None

    @cached_property  # type: ignore[no-redef]
    def fragment(self):
        """
        Retrieve the fragment within a document referenced by this Notification, if any.

        This assumes the underlying object won't disappear, as there is no SQL foreign
        key constraint enforcing a link.
        """
        if self.fragment_uuid and self.fragment_model:
            return self.fragment_model.query.filter_by(uuid=self.fragment_uuid).one()
        return None

    @classmethod
    def renderer(cls, view: Type[T]) -> Type[T]:
        """
        Register a view class containing render methods.

        Usage in views::

            from ..models import MyNotificationType
            from .views import NotificationView

            @MyNotificationType.renderer
            class MyNotificationView(NotificationView):
                ...
        """
        if cls.cls_type() in cls.renderers:
            raise TypeError(
                f"A renderer has already been registered for {cls.cls_type()}"
            )
        cls.renderers[cls.cls_type()] = view
        return view

    @classmethod
    def allow_transport(cls, transport) -> bool:
        """Return ``cls.allow_<transport>``."""
        return getattr(cls, 'allow_' + transport)

    @property
    def role_provider_obj(self):
        """Return fragment if exists, document otherwise, indicating role provider."""
        return self.fragment or self.document

    def dispatch(self) -> Generator[UserNotification, None, None]:
        """
        Create :class:`UserNotification` instances and yield in an iterator.

        This is a heavy method and must be called from a background job. When making
        new notifications, it will revoke previous notifications issued against the
        same document.

        Subclasses wanting more control over how their notifications are dispatched
        should override this method.
        """
        for user, role in self.role_provider_obj.actors_with(
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
            if not user.state.ACTIVE:
                continue

            # Was a notification already sent to this user? If so:
            # 1. The user has multiple roles
            # 2. We're being dispatched a second time, possibly because a background
            #    job failed and is re-queued.
            # In either case, don't notify the user a second time.

            # Since this query uses SQLAlchemy's session cache, we don't have to
            # bother with a local cache for the first case.
            existing_notification = UserNotification.query.get((user.id, self.eventid))
            if existing_notification is None:
                user_notification = UserNotification(
                    eventid=self.eventid,
                    user_id=user.id,
                    notification_id=self.id,
                    role=role,
                )
                db.session.add(user_notification)
                yield user_notification

    # Make :attr:`type_` available under the name `type`, but declare this at the very
    # end of the class to avoid conflicts with the Python `type` global that is
    # used for type-hinting
    type = db.synonym('type_')


class PreviewNotification:
    """
    Mimics a Notification subclass without instantiating it, for providing a preview.

    To be used with :class:`NotificationFor`::

        NotificationFor(PreviewNotification(NotificationType), user)
    """

    def __init__(self, cls, document, fragment=None) -> None:
        self.eventid = self.eventid_b58 = self.id = 'preview'  # May need to be a UUID
        self.cls = cls
        self.document = document
        self.document_uuid = document.uuid
        self.fragment = fragment
        self.fragment_uuid = fragment.uuid

    def __getattr__(self, attr: str):
        """Get an attribute."""
        return getattr(self.cls, attr)


class UserNotificationMixin:
    """Shared mixin for :class:`UserNotification` and :class:`NotificationFor`."""

    notification: Notification

    @property
    def notification_type(self) -> str:
        return self.notification.type

    with_roles(notification_type, read={'owner'})

    @property
    def document(self) -> Optional[db.Model]:
        """Document that this notification is for."""
        return self.notification.document

    with_roles(document, read={'owner'})

    @property
    def fragment(self) -> Optional[db.Model]:
        """Fragment within this document that this notification is for."""
        return self.notification.fragment

    with_roles(fragment, read={'owner'})

    # This dummy property is required because of a pending mypy issue:
    # https://github.com/python/mypy/issues/4125
    @property
    def is_revoked(self) -> bool:
        raise NotImplementedError("Subclass must provide this property")

    @is_revoked.setter
    def is_revoked(self, value: bool) -> None:
        raise NotImplementedError("Subclass must provide this property")

    def is_not_deleted(self, revoke: bool = False) -> bool:
        """
        Return True if the document and optional fragment are still present.

        :param bool revoke: Mark the notification as revoked if document or fragment
            is missing
        """
        try:
            return bool(self.fragment and self.document or self.document)
        except NoResultFound:
            pass
        if revoke:
            self.is_revoked = True
            # Do not set self.rollupid because this is not a rollup
        return False


class UserNotification(UserNotificationMixin, NoIdMixin, db.Model):
    """
    The recipient of a notification.

    Contains delivery metadata and helper methods to render the notification.
    """

    __tablename__ = 'user_notification'

    # Primary key is a compound of (user_id, eventid).

    #: Id of user being notified
    user_id = immutable(
        db.Column(
            None,
            db.ForeignKey('user.id', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )

    #: User being notified (backref defined below, outside the model)
    user = with_roles(
        immutable(db.relationship(User)), read={'owner'}, grants={'owner'}
    )

    #: Random eventid, shared with the Notification instance
    eventid = with_roles(
        immutable(db.Column(UUIDType(binary=False), primary_key=True, nullable=False)),
        read={'owner'},
    )

    #: Id of notification that this user received
    notification_id = immutable(
        db.Column(None, nullable=False)
    )  # fkey in __table_args__ below
    #: Notification that this user received
    notification = with_roles(
        immutable(
            db.relationship(
                Notification, backref=db.backref('recipients', lazy='dynamic')
            )
        ),
        read={'owner'},
    )

    #: The role they held at the time of receiving the notification, used for
    #: customizing the template.
    #:
    #: Note: This column represents the first instance of a role shifting from being an
    #: entirely in-app symbol (i.e., code refactorable) to being data in the database
    #: (i.e., requiring a data migration alongside a code refactor)
    role = with_roles(immutable(db.Column(db.Unicode, nullable=False)), read={'owner'})

    #: Timestamp for when this notification was marked as read
    read_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), default=None, nullable=True),
        read={'owner'},
    )

    #: Timestamp when/if the notification is revoked. This can happen if:
    #: 1. The action that caused the notification has been undone (future use)
    #: 2. A new notification has been raised for the same document and this user was
    #:    a recipient of the new notification
    #: 3. The underlying document or fragment has been deleted
    revoked_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'owner'},
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
            'eventid_b58',
            'role',
            'read_at',
            'is_read',
            'is_revoked',
            'rollupid',
            'notification_type',
        },
        'related': {
            'created_at',
            'eventid',
            'eventid_b58',
            'role',
            'read_at',
            'is_read',
            'is_revoked',
            'rollupid',
        },
    }

    # --- User notification properties -------------------------------------------------

    @property
    def identity(self) -> Tuple[int, UUID]:
        """Primary key of this object."""
        return (self.user_id, self.eventid)

    @hybrid_property
    def eventid_b58(self) -> str:
        """URL-friendly UUID representation, using Base58 with the Bitcoin alphabet."""
        return uuid_to_base58(self.eventid)

    @eventid_b58.setter
    def eventid_b58(self, value: str):
        self.eventid = uuid_from_base58(value)

    @eventid_b58.comparator
    def eventid_b58(cls):
        return SqlUuidB58Comparator(cls.eventid)

    with_roles(eventid_b58, read={'owner'})

    @hybrid_property
    def is_read(self) -> bool:
        """Whether this notification has been marked as read."""
        return self.read_at is not None

    @is_read.setter
    def is_read(self, value: bool) -> None:
        if value:
            if not self.read_at:
                self.read_at = db.func.utcnow()
        else:
            self.read_at = None

    @is_read.expression
    def is_read(cls):
        return cls.read_at.isnot(None)

    with_roles(is_read, rw={'owner'})

    @hybrid_property
    def is_revoked(self) -> bool:
        """Whether this notification has been marked as revoked."""
        return self.revoked_at is not None

    @is_revoked.setter
    def is_revoked(self, value: bool) -> None:
        if value:
            if not self.revoked_at:
                self.revoked_at = db.func.utcnow()
        else:
            self.revoked_at = None

    @is_revoked.expression
    def is_revoked(cls):
        return cls.revoked_at.isnot(None)

    with_roles(is_revoked, rw={'owner'})

    # --- Dispatch helper methods ------------------------------------------------------

    def user_preferences(self) -> NotificationPreferences:
        """Return the user's notification preferences for this notification type."""
        prefs = self.user.notification_preferences.get(self.notification_type)
        if prefs is None:
            prefs = NotificationPreferences(
                user=self.user, notification_type=self.notification_type
            )
            db.session.add(prefs)
            self.user.notification_preferences[self.notification_type] = prefs
        return prefs

    def has_transport(self, transport: str) -> bool:
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

    def transport_for(self, transport: str) -> Optional[Union[UserEmail, UserPhone]]:
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

    def rollup_previous(self) -> None:
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
                UserNotification.revoked_at.is_(None),
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
                    UserNotification.revoked_at.is_(None),
                    # Earlier instance shares our rollupid
                    UserNotification.rollupid == self.rollupid,
                )
                .options(
                    db.load_only(
                        UserNotification.user_id,
                        UserNotification.eventid,
                        UserNotification.revoked_at,
                        UserNotification.rollupid,
                    )
                )
            ):
                previous.is_revoked = True
                previous.rollupid = self.rollupid

    def rolledup_fragments(self) -> Optional[Query]:
        """Return all fragments in the rolled up batch as a base query."""
        if not self.notification.fragment_model:
            return None
        # Return a query on the fragment model with the rolled up identifiers
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
    def get_for(cls, user: User, eventid_b58: str) -> Optional[UserNotification]:
        """Retrieve a :class:`UserNotification` using SQLAlchemy session cache."""
        return cls.query.get((user.id, uuid_from_base58(eventid_b58)))

    @classmethod
    def web_notifications_for(cls, user: User, unread_only: bool = False) -> Query:
        query = UserNotification.query.join(Notification).filter(
            Notification.type.in_(notification_web_types),
            UserNotification.user == user,
            UserNotification.revoked_at.is_(None),
        )
        if unread_only:
            query = query.filter(UserNotification.read_at.is_(None))
        return query.order_by(Notification.created_at.desc())

    @classmethod
    def unread_count_for(cls, user: User) -> int:
        return (
            UserNotification.query.join(Notification)
            .filter(
                Notification.type.in_(notification_web_types),
                UserNotification.user == user,
                UserNotification.read_at.is_(None),
                UserNotification.revoked_at.is_(None),
            )
            .count()
        )

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
        for user_notification in cls.query.filter_by(user_id=old_user.id).all():
            existing = cls.query.get((new_user.id, user_notification.eventid))
            # TODO: Instead of dropping old_user's dupe notifications, check which of
            # the two has a higher priority role and keep that. This may not be possible
            # if the two copies are for different notifications under the same eventid.
            if existing is not None:
                db.session.delete(user_notification)
        cls.query.filter_by(user_id=old_user.id).update(
            {'user_id': new_user.id}, synchronize_session=False
        )
        return None


class NotificationFor(UserNotificationMixin):
    """View-only wrapper to mimic :class:`UserNotification`."""

    identity = read_at = revoked_at = None
    is_revoked = is_read = False

    def __init__(self, notification, user) -> None:
        self.notification = notification
        self.eventid = notification.eventid
        self.notification_id = notification.id

        self.user = user
        self.user_id = user.id

    @property
    def role(self) -> Optional[str]:
        """User's primary matching role for this notification."""
        if self.document and self.user:
            roles = self.document.roles_for(self.user)
            for role in self.notification.roles:
                if role in roles:
                    return role
        return None

    def rolledup_fragments(self) -> Optional[Query]:
        """Return a query to load the notification fragment."""
        if not self.notification.fragment_model:
            return None
        return self.notification.fragment_model.query.filter_by(
            uuid=self.notification.fragment_uuid
        )


# --- Notification preferences ---------------------------------------------------------


class NotificationPreferences(BaseMixin, db.Model):
    """Holds a user's preferences for a particular :class:`Notification` type."""

    __tablename__ = 'notification_preferences'

    #: Id of user whose preferences are represented here
    user_id = immutable(
        db.Column(
            None,
            db.ForeignKey('user.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        )
    )
    #: User whose preferences are represented here
    user = with_roles(
        immutable(db.relationship(User, back_populates='notification_preferences')),
        read={'owner'},
        grants={'owner'},
    )

    # Notification type, corresponding to Notification.type (a class attribute there)
    # notification_type = '' holds the veto switch to disable a transport entirely
    notification_type = immutable(db.Column(db.Unicode, nullable=False))

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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.user:
            self.set_defaults()

    def __repr__(self) -> str:
        """Represent :class:`NotificationPreferences` as a string."""
        return (
            f'NotificationPreferences('
            f'notification_type={self.notification_type!r}, user={self.user!r}'
            f')'
        )

    def set_defaults(self) -> None:
        """Set defaults based on the type's defaults, and previous user prefs."""
        transport_attrs = (
            ('by_email', 'default_email'),
            ('by_sms', 'default_sms'),
            ('by_webpush', 'default_webpush'),
            ('by_telegram', 'default_telegram'),
            ('by_whatsapp', 'default_whatsapp'),
        )
        with db.session.no_autoflush:
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
                    for t_attr, _d_attr in transport_attrs:
                        if getattr(self, t_attr) is None:
                            setattr(self, t_attr, True)
            else:
                for t_attr, _d_attr in transport_attrs:
                    if getattr(self, t_attr) is None:
                        # If this transport is enabled for any existing notification
                        # type, also enable here.
                        setattr(
                            self,
                            t_attr,
                            any(
                                getattr(np, t_attr)
                                for np in self.user.notification_preferences.values()
                            ),
                        )

    @with_roles(call={'owner'})
    def by_transport(self, transport: str) -> bool:
        """Return ``self.by_<transport>``."""
        return getattr(self, 'by_' + transport)

    @with_roles(call={'owner'})
    def set_transport(self, transport: str, value: bool) -> None:
        """Set a preference for a transport."""
        setattr(self, 'by_' + transport, value)

    @cached_property
    def type_cls(self) -> Optional[Notification]:
        """Return the Notification subclass corresponding to self.notification_type."""
        # Use `registry.get(type)` instead of `registry[type]` because the user may have
        # saved preferences for a discontinued notification type. These should ideally
        # be dropped in migrations, but it's possible for the data to be outdated.
        return notification_type_registry.get(self.notification_type)

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
        for ntype, prefs in list(old_user.notification_preferences.items()):
            if ntype in new_user.notification_preferences:
                db.session.delete(prefs)
        NotificationPreferences.query.filter_by(user_id=old_user.id).update(
            {'user_id': new_user.id}, synchronize_session=False
        )
        return None

    @db.validates('notification_type')
    def _valid_notification_type(self, key: str, value: Optional[str]) -> str:
        if value == '':  # Special-cased name for main preferences
            return value
        if value is None or value not in notification_type_registry:
            raise ValueError("Invalid notification_type: %s" % value)
        return value


@reopen(User)
class __User:
    all_notifications = with_roles(
        db.relationship(
            UserNotification,
            lazy='dynamic',
            order_by=UserNotification.created_at.desc(),
            viewonly=True,
        ),
        read={'owner'},
    )

    notification_preferences = db.relationship(
        NotificationPreferences,
        collection_class=column_mapped_collection(
            NotificationPreferences.notification_type
        ),
        back_populates='user',
    )

    # This relationship is wrapped in a property that creates it on first access
    _main_notification_preferences = db.relationship(
        NotificationPreferences,
        primaryjoin=db.and_(
            NotificationPreferences.user_id == User.id,
            NotificationPreferences.notification_type == '',
        ),
        uselist=False,
        viewonly=True,
    )

    @cached_property
    def main_notification_preferences(self) -> NotificationPreferences:
        if not self._main_notification_preferences:
            main = NotificationPreferences(
                user=self,
                notification_type='',
                by_email=True,
                by_sms=False,
                by_webpush=False,
                by_telegram=False,
                by_whatsapp=False,
            )
            db.session.add(main)
            return main
        return self._main_notification_preferences


# --- Signal handlers ------------------------------------------------------------------


auto_init_default(Notification.eventid)


@event.listens_for(Notification, 'mapper_configured', propagate=True)
def _register_notification_types(mapper_, cls) -> None:
    # Don't register the base class itself, or inactive types
    if cls is not Notification:
        # Tell mypy what type of class we're processing
        assert issubclass(cls, Notification)  # nosec

        # Populate cls with helper attributes

        type_hints = get_type_hints(cls, localns=vars(models))
        cls.document_model = (
            type_hints['document']
            if isinstance(type_hints['document'], type)
            and issubclass(type_hints['document'], db.Model)
            else None
        )
        cls.document_type = (
            cls.document_model.__tablename__  # type: ignore[attr-defined]
            if cls.document_model
            else None
        )
        cls.fragment_model = (
            type_hints['fragment']
            if isinstance(type_hints['fragment'], type)
            and issubclass(type_hints['fragment'], db.Model)
            else None
        )
        cls.fragment_type = (
            cls.fragment_model.__tablename__  # type: ignore[attr-defined]
            if cls.fragment_model
            else None
        )

        # Exclude inactive notifications in the registry. It is used to populate the
        # user's notification preferences screen.
        if cls.active:
            notification_type_registry[
                cls.__mapper_args__['polymorphic_identity']
            ] = cls
        # Include inactive notifications in the web types, as this is used for the web
        # feed of past notifications, including deprecated (therefore inactive) types
        if cls.allow_web:
            notification_web_types.add(cls.__mapper_args__['polymorphic_identity'])
