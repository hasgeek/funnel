"""
Notification primitives.

Notification models and support classes for implementing notifications, best understood
using examples:

Scenario: Notification about an update
    Given: User A is a participant in project P When: Project P's editor E posts an
    update U Then: User A receives a notification about update U And: The notification
    is attributed to editor E And: User A is informed of being a recipient for being a
    participant in project P And: User A can choose to unsubscribe from notifications
    about updates

How it works:

1. The view handler that creates the Update triggers an UpdateNotification on it. This
    is a subclass of Notification. The UpdateNotification class specifies the roles that
    must receive the notification.

2. Roles? Yes. UpdateNotification says it should be delivered to users possessing the
    roles 'project_crew' and 'project_participant' on the Update object, in that order.
    That means a user who is both crew and participant will only get the version meant
    for crew members and won't be notified twice. Versions will have minor differences
    such as in language: "the project you're a crew member of had an update", versus
    "the project you're a participant of had an update".

3. The view calls `dispatch_notification` with an instance of UpdateNotification
    referring to the Update instance. The dispatcher can process multiple such
    notifications at once, tagging them with a common eventid. It queues a background
    worker in RQ to process the notifications.

4. The background worker calls `UpdateNotification.dispatch` to find all recipients and
    create `UserNotification` instances for each of them. The worker can be given
    multiple notifications linked to the same event. If a user is identified as a
    recipient to more than one notification, only the first match is used. To find
    these recipients, the default notification-level dispatch method calls
    `Update.actors_for({roles})`. The default implementation in RoleMixin is aware that
    these roles are inherited from Project (using granted_via declarations), and so
    it calls `Update.project.actors_for`. The obtained UserNotification instances are
    batched and handed off to a second round of background workers.

5. Each second background worker receives a batch of UserNotification instances and
    discovers user preferences for the particular notification. Some notifications are
    defined as being for a fragment of a larger document, like for an individual
    comment in a large comment thread. In such a case, a scan is performed for previous
    unread instances of UserNotification referring to the same document, determined
    from `UserNotification.notification.document_uuid`, and those are revoked to remove
    them from the user's feed. A rollup is presented instead, showing all fragments
    since the last view or last day, whichever is greater. The second background worker
    now queues a third series of background workers, for each of the supported
    transports if at least one recipient in that batch wants to use that transport.

6. A separate render view class named RenderNewUpdateNotification contains methods named
    like `web`, `email`, `sms` and others. These are expected to return a rendered
    message. The `web` render is used for the notification feed page on the website.

7. Views are registered to the model, so the dispatch mechanism only needs to call
    ``view.email()`` etc to get the rendered content. The dispatch mechanism then calls
    the appropriate transport helper (``send_email``, etc) to do the actual sending. The
    message id returned by these functions is saved to the ``messageid_*`` columns in
    UserNotification, as a record that the notification was sent. If the transport
    doesn't support message ids, a random non-None value is used. Accurate message ids
    are only required when user interaction over the same transport is expected, such
    as reply emails.

10. The ``/updates`` endpoint on the website shows a feed of UserNotification items and
    handles the ability to mark each as read.

It is possible to have two separate notifications for the same event. For example, a
comment replying to another comment will trigger a CommentReplyNotification to the user
being replied to, and a ProjectCommentNotification or ProposalCommentNotification for
the project or proposal. The same user may be a recipient of both notifications. To
de-duplicate this, a random "eventid" is shared across both notifications, and is
required to be unique per user, so that the second notification will be skipped. This is
supported using an unusual primary and foreign key structure in :class:`Notification`
and :class:`UserNotification`:

1. Notification has pkey ``(eventid, id)``, where `id` is local to the instance
2. UserNotification has pkey ``(recipient_id, eventid)`` combined with a fkey to
    Notification using ``(eventid, notification_id)``
"""
from __future__ import annotations

from collections.abc import Callable, Generator, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import (
    Any,
    ClassVar,
    Generic,
    Optional,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)
from typing_extensions import Protocol, get_original_bases
from uuid import UUID, uuid4

from sqlalchemy import event
from sqlalchemy.orm import column_keyed_dict
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import (
    Registry,
    SqlUuidB58Comparator,
    auto_init_default,
    immutable,
    with_roles,
)
from coaster.utils import LabeledEnum, uuid_from_base58, uuid_to_base58

from ..typing import T
from . import (
    BaseMixin,
    DynamicMapped,
    Mapped,
    Model,
    NoIdMixin,
    Query,
    backref,
    db,
    hybrid_property,
    postgresql,
    relationship,
    sa,
)
from .account import Account, AccountEmail, AccountPhone
from .helpers import reopen
from .phone_number import PhoneNumber, PhoneNumberMixin
from .typing import UuidModelUnion

__all__ = [
    'SMS_STATUS',
    'notification_categories',
    'SmsMessage',
    'NotificationType',
    'Notification',
    'PreviewNotification',
    'NotificationPreferences',
    'NotificationRecipient',
    'NotificationFor',
    'notification_type_registry',
    'notification_web_types',
]

# --- Typing ---------------------------------------------------------------------------

# Document generic type
_D = TypeVar('_D', bound=UuidModelUnion)
# Fragment generic type
_F = TypeVar('_F', bound=Optional[UuidModelUnion])
# Type of None (required to detect Optional)
NoneType = type(None)

# --- Registries -----------------------------------------------------------------------

#: Registry of Notification subclasses for user preferences, automatically populated.
#: Inactive types and types that shadow other types are excluded from this registry
notification_type_registry: dict[str, type[Notification]] = {}
#: Registry of notification types that allow web renders
notification_web_types: set[str] = set()


@dataclass
class NotificationCategory:
    """Category for a notification."""

    priority_id: int
    title: str
    available_for: Callable[[Account], bool]


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
            db.session.query(user.rsvps.exists()).scalar()  # type: ignore[has-type]
            or db.session.query(  # type: ignore[has-type]
                user.proposal_memberships.exists()
            ).scalar()
        ),
    ),
    project_crew=NotificationCategory(
        4,
        __("Projects I am a crew member in"),
        # Criteria: user has ever been a project crew member
        lambda user: db.session.query(  # type: ignore[has-type]
            user.projects_as_crew_memberships.exists()
        ).scalar(),
    ),
    account_admin=NotificationCategory(
        5,
        __("Accounts I manage"),
        # Criteria: user has ever been an organization admin
        lambda user: db.session.query(  # type: ignore[has-type]
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


class SMS_STATUS(LabeledEnum):  # noqa: N801
    """SMS delivery status."""

    QUEUED = (1, __("Queued"))
    PENDING = (2, __("Pending"))
    DELIVERED = (3, __("Delivered"))
    FAILED = (4, __("Failed"))
    UNKNOWN = (5, __("Unknown"))


# --- Legacy models --------------------------------------------------------------------


class SmsMessage(PhoneNumberMixin, BaseMixin, Model):
    """An outbound SMS message."""

    __tablename__ = 'sms_message'
    __phone_optional__ = False
    __phone_unique__ = False
    __phone_is_exclusive__ = False
    phone_number_reference_is_active: bool = False

    transactionid: Mapped[str | None] = immutable(
        sa.orm.mapped_column(sa.UnicodeText, unique=True, nullable=True)
    )
    # The message itself
    message: Mapped[str] = immutable(
        sa.orm.mapped_column(sa.UnicodeText, nullable=False)
    )
    # Flags
    status: Mapped[int] = sa.orm.mapped_column(
        sa.Integer, default=SMS_STATUS.QUEUED, nullable=False
    )
    status_at: Mapped[datetime | None] = sa.orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    fail_reason: Mapped[str | None] = sa.orm.mapped_column(
        sa.UnicodeText, nullable=True
    )

    def __init__(self, **kwargs) -> None:
        phone = kwargs.pop('phone', None)
        if phone:
            kwargs['phone_number'] = PhoneNumber.add(phone)
        super().__init__(**kwargs)


# --- Notification models --------------------------------------------------------------


class NotificationType(Generic[_D, _F], Protocol):
    """Protocol for :class:`Notification` and :class:`PreviewNotification`."""

    type: str  # noqa: A003
    eventid: UUID
    id: UUID  # noqa: A003
    eventid_b58: str
    document: _D
    document_uuid: UUID
    fragment: _F | None
    fragment_uuid: UUID | None
    created_by_id: int | None
    created_by: Account | None


class Notification(NoIdMixin, Model, Generic[_D, _F]):
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
    active: ClassVar[bool] = True

    #: Random identifier for the event that triggered this notification. Event ids can
    #: be shared across notifications, and will be used to enforce a limit of one
    #: instance of a UserNotification per-event rather than per-notification
    eventid: Mapped[UUID] = immutable(
        sa.orm.mapped_column(
            postgresql.UUID, primary_key=True, nullable=False, default=uuid4
        )
    )

    #: Notification id
    id: Mapped[UUID] = immutable(  # noqa: A003
        sa.orm.mapped_column(
            postgresql.UUID, primary_key=True, nullable=False, default=uuid4
        )
    )

    #: Default category of notification. Subclasses MUST override
    category: ClassVar[NotificationCategory] = notification_categories.none
    #: Default description for notification. Subclasses MUST override
    title: ClassVar[str] = __("Unspecified notification type")
    #: Default description for notification. Subclasses MUST override
    description: ClassVar[str] = ''
    #: Type of Notification subclass (auto-populated from subclass's `type=` parameter)
    cls_type: ClassVar[str] = ''
    #: Type for user preferences, in case a notification type is a shadow of
    #: another type (auto-populated from subclass's `shadow=` parameter)
    pref_type: ClassVar[str] = ''

    #: Document model, must be specified in subclasses
    document_model: ClassVar[type[UuidModelUnion]]
    #: SQL table name for document type, auto-populated from the document model
    document_type: ClassVar[str]

    #: Fragment model, optional for subclasses
    fragment_model: ClassVar[type[UuidModelUnion] | None] = None
    #: SQL table name for fragment type, auto-populated from the fragment model
    fragment_type: ClassVar[str | None]

    #: Roles to send notifications to. Roles must be in order of priority for situations
    #: where a user has more than one role on the document.
    roles: ClassVar[Sequence[str]] = []

    #: Exclude triggering actor from receiving notifications? Subclasses may override
    exclude_actor: ClassVar[bool] = False

    #: If this notification is typically for a single recipient, views will need to be
    #: careful about leaking out recipient identifiers such as a utm_source tracking tag
    for_private_recipient: ClassVar[bool] = False

    #: The preference context this notification is being served under. Users may have
    #: customized preferences per account (nee profile) or project
    preference_context: ClassVar[Any] = None

    #: Notification type (identifier for subclass of :class:`NotificationType`)
    type_: Mapped[str] = immutable(
        sa.orm.mapped_column('type', sa.Unicode, nullable=False)
    )

    #: Id of user that triggered this notification
    created_by_id: Mapped[int | None] = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('account.id', ondelete='SET NULL'), nullable=True
    )
    #: User that triggered this notification. Optional, as not all notifications are
    #: caused by user activity. Used to optionally exclude user from receiving
    #: notifications of their own activity
    created_by: Mapped[Account | None] = relationship(Account)

    #: UUID of document that the notification refers to
    document_uuid: Mapped[UUID] = immutable(
        sa.orm.mapped_column(postgresql.UUID, nullable=False, index=True)
    )

    #: Optional fragment within document that the notification refers to. This may be
    #: the document itself, or something within it, such as a comment. Notifications for
    #: multiple fragments are collapsed into a single notification
    fragment_uuid: Mapped[UUID | None] = immutable(
        sa.orm.mapped_column(postgresql.UUID, nullable=True)
    )

    __table_args__ = (
        # This could have been achieved with a UniqueConstraint on all three columns.
        # When the third column (fragment_uuid) is null it has the same effect as the
        # PostgreSQL-specific where clause. We use the clause here to make clear our
        # intent of only enforcing a one-notification limit when the fragment is
        # present. Hence the naming convention of `_key` suffix rather than `ix_` prefix
        sa.Index(
            'notification_type_document_uuid_fragment_uuid_key',
            type_,
            document_uuid,
            fragment_uuid,
            unique=True,
            postgresql_where=fragment_uuid.is_not(None),
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
    allow_web: ClassVar[bool] = True
    #: This notification class may be delivered by email
    allow_email: ClassVar[bool] = True
    #: This notification class may be delivered by SMS
    allow_sms: ClassVar[bool] = True
    #: This notification class may be delivered by push notification
    allow_webpush: ClassVar[bool] = True
    #: This notification class may be delivered by Telegram message
    allow_telegram: ClassVar[bool] = True
    #: This notification class may be delivered by WhatsApp message
    allow_whatsapp: ClassVar[bool] = True

    # Flags to set defaults for transports, in case the user has not made a choice

    #: By default, turn on/off delivery by email
    default_email: ClassVar[bool] = True
    #: By default, turn on/off delivery by SMS
    default_sms: ClassVar[bool] = True
    #: By default, turn on/off delivery by push notification
    default_webpush: ClassVar[bool] = True
    #: By default, turn on/off delivery by Telegram message
    default_telegram: ClassVar[bool] = True
    #: By default, turn on/off delivery by WhatsApp message
    default_whatsapp: ClassVar[bool] = True

    #: Ignore transport errors? If True, an error will be ignored silently. If False,
    #: an error report will be logged for the user or site administrator. TODO
    ignore_transport_errors: ClassVar[bool] = False

    #: Registry of per-class renderers ``{cls_type: CustomNotificationView}``
    renderers: ClassVar[dict[str, type]] = {}
    # Can't import RenderNotification from views here, so it's typed to just Type

    def __init_subclass__(  # pylint: disable=arguments-differ
        cls,
        type: str,  # noqa: A002  # pylint: disable=redefined-builtin
        shadows: type[Notification] | None = None,
        **kwargs,
    ) -> None:
        # For SQLAlchemy's polymorphic support
        if '__mapper_args__' not in cls.__dict__:
            cls.__mapper_args__ = {}
        cls.__mapper_args__['polymorphic_identity'] = type

        # Get document and fragment models from type hints
        for base in get_original_bases(cls):
            if get_origin(base) is Notification:
                document_model, fragment_model = get_args(base)
                if fragment_model is NoneType:
                    fragment_model = None
                elif get_origin(fragment_model) is Optional:
                    fragment_model = get_args(fragment_model)[0]
                elif get_origin(fragment_model) is Union:
                    _union_args = get_args(fragment_model)
                    if len(_union_args) == 2 and _union_args[1] is NoneType:
                        fragment_model = _union_args[0]
                    else:
                        raise TypeError(
                            f"Unsupported notification fragment: {fragment_model}"
                        )
                if 'document_model' in cls.__dict__:
                    if cls.document_model != document_model:
                        raise TypeError(f"{cls} has a conflicting document_model")
                else:
                    cls.document_model = document_model
                if 'fragment_model' in cls.__dict__:
                    if cls.fragment_model != fragment_model:
                        raise TypeError(f"{cls} has a conflicting fragment_model")
                else:
                    cls.fragment_model = fragment_model
                break

        cls.document_type = cls.document_model.__tablename__
        cls.fragment_type = (
            cls.fragment_model.__tablename__ if cls.fragment_model else None
        )

        # For notification type identification and preference management
        cls.cls_type = type
        if shadows is not None:
            if {'category', 'title', 'description'} & cls.__dict__.keys():
                raise TypeError(
                    "Shadow notification types cannot have category, title or"
                    " description as they are not shown in UI"
                )
            if shadows.cls_type != shadows.pref_type:
                raise TypeError(
                    f"{cls!r} cannot shadow {shadows!r} as it shadows yet another"
                    " notification type"
                )
            cls.pref_type = shadows.pref_type
        else:
            cls.pref_type = type

        return super().__init_subclass__(**kwargs)

    def __init__(
        self,
        document: _D | None = None,
        fragment: _F | None = None,
        **kwargs: Any,
    ) -> None:
        if document is not None:
            if not isinstance(document, self.document_model):
                raise TypeError(f"{document!r} is not of type {self.document_model!r}")
            kwargs['document_uuid'] = document.uuid
        if fragment is not None:
            if self.fragment_model is None:
                raise TypeError(f"{self.__class__} is not expecting a fragment")
            # Pylint can't parse the "is None" check above
            # pylint: disable=isinstance-second-argument-not-valid-type
            if not isinstance(fragment, self.fragment_model):
                raise TypeError(f"{fragment!r} is not of type {self.fragment_model!r}")
            kwargs['fragment_uuid'] = fragment.uuid
        super().__init__(**kwargs)

    @property
    def identity(self) -> tuple[UUID, UUID]:
        """Primary key of this object."""
        return (self.eventid, self.id)

    @hybrid_property
    def eventid_b58(self) -> str:
        """URL-friendly UUID representation, using Base58 with the Bitcoin alphabet."""
        return uuid_to_base58(self.eventid)

    @eventid_b58.inplace.setter
    def _eventid_b58_setter(self, value: str) -> None:
        self.eventid = uuid_from_base58(value)

    @eventid_b58.inplace.comparator
    @classmethod
    def _eventid_b58_comparator(cls) -> SqlUuidB58Comparator:
        """Return SQL comparator for Base58 rendering."""
        return SqlUuidB58Comparator(cls.eventid)

    @cached_property
    def document(self) -> _D:
        """
        Retrieve the document referenced by this Notification.

        This assumes the underlying object won't disappear, as there is no SQL foreign
        key constraint enforcing a link. The proper way to do this is by having a
        secondary table for each type of document.
        """
        if self.document_uuid and self.document_model:
            return cast(
                _D, self.document_model.query.filter_by(uuid=self.document_uuid).one()
            )
        raise RuntimeError(
            "This notification is missing document_model or document_uuid"
        )

    @cached_property
    def fragment(self) -> _F | None:
        """
        Retrieve the fragment within a document referenced by this Notification, if any.

        This assumes the underlying object won't disappear, as there is no SQL foreign
        key constraint enforcing a link.
        """
        if self.fragment_uuid and self.fragment_model:
            return cast(
                _F, self.fragment_model.query.filter_by(uuid=self.fragment_uuid).one()
            )
        return None

    @classmethod
    def renderer(cls, view: type[T]) -> type[T]:
        """
        Register a view class containing render methods.

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
    def allow_transport(cls, transport: str) -> bool:
        """Return ``cls.allow_<transport>``."""
        return getattr(cls, 'allow_' + transport)

    @property
    def role_provider_obj(self) -> _F | _D:
        """Return fragment if exists, document otherwise, indicating role provider."""
        return cast(Union[_F, _D], self.fragment or self.document)

    def dispatch(self) -> Generator[NotificationRecipient, None, None]:
        """
        Create :class:`UserNotification` instances and yield in an iterator.

        This is a heavy method and must be called from a background job. It creates
        instances of :class:`UserNotification` for each discovered recipient and yields
        them, skipping over pre-existing instances (typically caused by a second
        dispatch on the same event, such as when a background job fails midway and is
        restarted).

        Subclasses wanting more control over how their notifications are dispatched
        should override this method.
        """
        for account, role in self.role_provider_obj.actors_with(
            self.roles, with_role=True
        ):
            # If this notification requires that it not be sent to the actor that
            # triggered the notification, don't notify them. For example, a user who
            # leaves a comment should not be notified of their own comment. This `if`
            # condition uses `created_by_id` instead of the recommended `created_by` for
            # faster processing in a loop.
            if (
                self.exclude_actor
                and self.created_by_id is not None
                and self.created_by_id == account.id
            ):
                continue

            # Don't notify inactive (suspended, merged) users
            if not account.state.ACTIVE:
                continue

            # Was a notification already sent to this user? If so:
            # 1. The user has multiple roles
            # 2. We're being dispatched a second time, possibly because a background
            #    job failed and is re-queued.
            # In either case, don't notify the user a second time.

            # Since this query uses SQLAlchemy's session cache, we don't have to
            # bother with a local cache for the first case.
            existing_notification = NotificationRecipient.query.get(
                (account.id, self.eventid)
            )
            if existing_notification is None:
                recipient = NotificationRecipient(
                    eventid=self.eventid,
                    recipient_id=account.id,
                    notification_id=self.id,
                    role=role,
                )
                db.session.add(recipient)
                yield recipient

    # Make :attr:`type_` available under the name `type`, but declare this at the very
    # end of the class to avoid conflicts with the Python `type` global that is
    # used for type-hinting
    type: Mapped[str] = sa.orm.synonym('type_')  # noqa: A003


class PreviewNotification(NotificationType):
    """
    Mimics a Notification subclass without instantiating it, for providing a preview.

    To be used with :class:`NotificationFor`::

        NotificationFor(
            PreviewNotification(NotificationType, document, fragment, actor),
            recipient
        )
    """

    def __init__(  # pylint: disable=super-init-not-called
        self,
        cls: type[Notification],
        document: UuidModelUnion,
        fragment: UuidModelUnion | None = None,
        user: Account | None = None,
    ) -> None:
        self.eventid = uuid4()
        self.id = uuid4()
        self.eventid_b58 = uuid_to_base58(self.eventid)
        self.cls = cls
        self.type = cls.cls_type
        self.document = document
        self.document_uuid = document.uuid
        self.fragment = fragment
        self.fragment_uuid = fragment.uuid if fragment is not None else None
        self.created_by = user
        self.created_by_id = cast(int, user.id) if user is not None else None

    def __getattr__(self, attr: str) -> Any:
        """Get an attribute."""
        return getattr(self.cls, attr)


class NotificationRecipientMixin:
    """Shared mixin for :class:`NotificationRecipient` and :class:`NotificationFor`."""

    notification: Mapped[Notification] | Notification | PreviewNotification

    @cached_property
    def notification_type(self) -> str:
        """Return the notification type identifier."""
        return self.notification.type

    with_roles(notification_type, read={'owner'})

    @cached_property
    def notification_pref_type(self) -> str:
        """Return the notification preference type identifier."""
        # This is dependent on SQLAlchemy using the appropriate subclass of
        # :class:`Notification` so that :attr:`~Notification.pref_type` has the correct
        # value
        return self.notification.pref_type

    with_roles(notification_pref_type, read={'owner'})

    @cached_property
    def document(self) -> UuidModelUnion | None:
        """Document that this notification is for."""
        return self.notification.document

    with_roles(document, read={'owner'})

    @cached_property
    def fragment(self) -> UuidModelUnion | None:
        """Fragment within this document that this notification is for."""
        return self.notification.fragment

    with_roles(fragment, read={'owner'})

    is_revoked: bool

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


class NotificationRecipient(NotificationRecipientMixin, NoIdMixin, Model):
    """
    The recipient of a notification.

    Contains delivery metadata and helper methods to render the notification.
    """

    __tablename__ = 'notification_recipient'

    # Primary key is a compound of (recipient_id, eventid).

    #: Id of user being notified
    recipient_id: Mapped[int] = immutable(
        sa.orm.mapped_column(
            sa.Integer,
            sa.ForeignKey('account.id', ondelete='CASCADE'),
            primary_key=True,
            nullable=False,
        )
    )

    #: User being notified (backref defined below, outside the model)
    recipient: Mapped[Account] = with_roles(
        relationship(Account), read={'owner'}, grants={'owner'}
    )

    #: Random eventid, shared with the Notification instance
    eventid: Mapped[UUID] = with_roles(
        immutable(
            sa.orm.mapped_column(postgresql.UUID, primary_key=True, nullable=False)
        ),
        read={'owner'},
    )

    #: Id of notification that this user received (fkey in __table_args__ below)
    notification_id: Mapped[UUID] = sa.orm.mapped_column(
        postgresql.UUID, nullable=False
    )

    #: Notification that this user received
    notification: Mapped[Notification] = with_roles(
        relationship(Notification, backref=backref('recipients', lazy='dynamic')),
        read={'owner'},
    )

    #: The role they held at the time of receiving the notification, used for
    #: customizing the template.
    #:
    #: Note: This column represents the first instance of a role shifting from being an
    #: entirely in-app symbol (i.e., code refactorable) to being data in the database
    #: (i.e., requiring a data migration alongside a code refactor)
    role: Mapped[str] = with_roles(
        immutable(sa.orm.mapped_column(sa.Unicode, nullable=False)), read={'owner'}
    )

    #: Timestamp for when this notification was marked as read
    read_at: Mapped[datetime | None] = with_roles(
        sa.orm.mapped_column(sa.TIMESTAMP(timezone=True), default=None, nullable=True),
        read={'owner'},
    )

    #: Timestamp when/if the notification is revoked. This can happen if:
    #: 1. The action that caused the notification has been undone (future use)
    #: 2. A new notification has been raised for the same document and this user was
    #:    a recipient of the new notification
    #: 3. The underlying document or fragment has been deleted
    revoked_at: Mapped[datetime | None] = with_roles(
        sa.orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'owner'},
    )

    #: When a roll-up is performed, record an identifier for the items rolled up
    rollupid: Mapped[UUID | None] = with_roles(
        sa.orm.mapped_column(postgresql.UUID, nullable=True, index=True),
        read={'owner'},
    )

    #: Message id for email delivery
    messageid_email: Mapped[str | None] = sa.orm.mapped_column(
        sa.Unicode, nullable=True
    )
    #: Message id for SMS delivery
    messageid_sms: Mapped[str | None] = sa.orm.mapped_column(sa.Unicode, nullable=True)
    #: Message id for web push delivery
    messageid_webpush: Mapped[str | None] = sa.orm.mapped_column(
        sa.Unicode, nullable=True
    )
    #: Message id for Telegram delivery
    messageid_telegram: Mapped[str | None] = sa.orm.mapped_column(
        sa.Unicode, nullable=True
    )
    #: Message id for WhatsApp delivery
    messageid_whatsapp: Mapped[str | None] = sa.orm.mapped_column(
        sa.Unicode, nullable=True
    )

    __table_args__ = (
        sa.ForeignKeyConstraint(
            [eventid, notification_id],
            [Notification.eventid, Notification.id],
            ondelete='CASCADE',
            name='notification_recipient_eventid_notification_id_fkey',
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
    def identity(self) -> tuple[int, UUID]:
        """Primary key of this object."""
        return (self.recipient_id, self.eventid)

    @hybrid_property
    def eventid_b58(self) -> str:
        """URL-friendly UUID representation, using Base58 with the Bitcoin alphabet."""
        return uuid_to_base58(self.eventid)

    @eventid_b58.inplace.setter
    def _eventid_b58_setter(self, value: str) -> None:
        self.eventid = uuid_from_base58(value)

    @eventid_b58.inplace.comparator
    @classmethod
    def _eventid_b58_comparator(cls) -> SqlUuidB58Comparator:
        """Return SQL comparator for Base58 representation."""
        return SqlUuidB58Comparator(cls.eventid)

    with_roles(eventid_b58, read={'owner'})

    @hybrid_property
    def is_read(self) -> bool:
        """Whether this notification has been marked as read."""
        return self.read_at is not None

    @is_read.inplace.setter
    def _is_read_setter(self, value: bool) -> None:
        if value:
            if not self.read_at:
                self.read_at = sa.func.utcnow()
        else:
            self.read_at = None

    @is_read.inplace.expression
    @classmethod
    def _is_read_expression(cls) -> sa.ColumnElement[bool]:
        """Test if notification has been marked as read, as a SQL expression."""
        return cls.read_at.is_not(None)

    with_roles(is_read, rw={'owner'})

    @hybrid_property
    def is_revoked(self) -> bool:  # type: ignore[override]
        """Whether this notification has been marked as revoked."""
        return self.revoked_at is not None

    @is_revoked.inplace.setter
    def _is_revoked_setter(self, value: bool) -> None:
        """Set or remove revoked_at timestamp."""
        if value:
            if not self.revoked_at:
                self.revoked_at = sa.func.utcnow()
        else:
            self.revoked_at = None

    @is_revoked.inplace.expression
    @classmethod
    def _is_revoked_expression(cls) -> sa.ColumnElement[bool]:
        """Return SQL Expression."""
        return cls.revoked_at.is_not(None)

    with_roles(is_revoked, rw={'owner'})

    # --- Dispatch helper methods ------------------------------------------------------

    def recipient_preferences(self) -> NotificationPreferences:
        """Return the account's notification preferences for this notification type."""
        prefs = self.recipient.notification_preferences.get(self.notification_pref_type)
        if prefs is None:
            prefs = NotificationPreferences(
                notification_type=self.notification_pref_type, account=self.recipient
            )
            db.session.add(prefs)
            self.recipient.notification_preferences[self.notification_pref_type] = prefs
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
        main_prefs = self.recipient.main_notification_preferences
        user_prefs = self.recipient_preferences()
        return (
            self.notification.allow_transport(transport)
            and main_prefs.by_transport(transport)
            and user_prefs.by_transport(transport)
            and self.recipient.has_transport(transport)
        )

    def transport_for(self, transport: str) -> AccountEmail | AccountPhone | None:
        """
        Return transport address for the requested transport.

        Uses four criteria:

        1. The notification type allows delivery over this transport
        2. The user's main transport preferences allow this one
        3. The user's per-type preference allows it
        4. The user has this transport (verified email or phone, etc)
        """
        main_prefs = self.recipient.main_notification_preferences
        user_prefs = self.recipient_preferences()
        if (
            self.notification.allow_transport(transport)
            and main_prefs.by_transport(transport)
            and user_prefs.by_transport(transport)
        ):
            return self.recipient.transport_for(
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

        # For rollup: find most recent unread -- or read but created in the last day --
        # that has a rollupid. Reuse that id so that the current notification becomes
        # the latest in that batch of rolled up notifications. If none, this is the
        # start of a new batch, so make a new id.
        rollupid = (
            db.session.query(NotificationRecipient.rollupid)
            .join(Notification)
            .filter(
                # Same user
                NotificationRecipient.recipient_id == self.recipient_id,
                # Same type of notification
                Notification.type == self.notification.type,
                # Same document
                Notification.document_uuid == self.notification.document_uuid,
                # Same reason for receiving notification as earlier instance (same role)
                NotificationRecipient.role == self.role,
                # Earlier instance is unread or within 24 hours
                sa.or_(
                    NotificationRecipient.read_at.is_(None),
                    # TODO: Hardcodes for PostgreSQL, turn this into a SQL func
                    # expression like func.utcnow()
                    NotificationRecipient.created_at
                    >= sa.text("NOW() - INTERVAL '1 DAY'"),
                ),
                # Earlier instance is not revoked
                NotificationRecipient.revoked_at.is_(None),
                # Earlier instance has a rollupid
                NotificationRecipient.rollupid.is_not(None),
            )
            .order_by(NotificationRecipient.created_at.asc())
            .limit(1)
            .scalar()
        )
        if not rollupid:
            # No previous rollupid? Then we're the first. The next notification
            # will use our rollupid as long as we're unread or within a day
            self.rollupid = uuid4()
        else:
            # Use the existing id, find all using it and revoke them
            self.rollupid = rollupid

            # Now rollup all previous unread. This will skip (a) previously revoked user
            # notifications, and (b) unrolled but read user notifications.
            for previous in (
                NotificationRecipient.query.join(Notification)
                .filter(
                    # Same user
                    NotificationRecipient.recipient_id == self.recipient_id,
                    # Not ourselves
                    NotificationRecipient.eventid != self.eventid,
                    # Same type of notification
                    Notification.type == self.notification.type,
                    # Same document
                    Notification.document_uuid == self.notification.document_uuid,
                    # Same role as earlier notification,
                    NotificationRecipient.role == self.role,
                    # Earlier instance is not revoked
                    NotificationRecipient.revoked_at.is_(None),
                    # Earlier instance shares our rollupid
                    NotificationRecipient.rollupid == self.rollupid,
                )
                .options(
                    sa.orm.load_only(
                        NotificationRecipient.recipient_id,
                        NotificationRecipient.eventid,
                        NotificationRecipient.revoked_at,
                        NotificationRecipient.rollupid,
                    )
                )
            ):
                previous.is_revoked = True
                previous.rollupid = self.rollupid

    def rolledup_fragments(self) -> Query | None:
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
                .select_from(NotificationRecipient)
                .join(NotificationRecipient.notification)
                .filter(NotificationRecipient.rollupid == self.rollupid)
            )
        )

    @classmethod
    def get_for(cls, user: Account, eventid_b58: str) -> NotificationRecipient | None:
        """Retrieve a :class:`UserNotification` using SQLAlchemy session cache."""
        return cls.query.get((user.id, uuid_from_base58(eventid_b58)))

    @classmethod
    def web_notifications_for(
        cls, user: Account, unread_only: bool = False
    ) -> Query[NotificationRecipient]:
        """Return web notifications for a user, optionally returning unread-only."""
        query = NotificationRecipient.query.join(Notification).filter(
            Notification.type.in_(notification_web_types),
            NotificationRecipient.recipient == user,
            NotificationRecipient.revoked_at.is_(None),
        )
        if unread_only:
            query = query.filter(NotificationRecipient.read_at.is_(None))
        return query.order_by(Notification.created_at.desc())

    @classmethod
    def unread_count_for(cls, user: Account) -> int:
        """Return unread notification count for a user."""
        return (
            NotificationRecipient.query.join(Notification)
            .filter(
                Notification.type.in_(notification_web_types),
                NotificationRecipient.recipient == user,
                NotificationRecipient.read_at.is_(None),
                NotificationRecipient.revoked_at.is_(None),
            )
            .count()
        )

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        for notification_recipient in cls.query.filter_by(
            recipient_id=old_account.id
        ).all():
            existing = cls.query.get((new_account.id, notification_recipient.eventid))
            # TODO: Instead of dropping old_user's dupe notifications, check which of
            # the two has a higher priority role and keep that. This may not be possible
            # if the two copies are for different notifications under the same eventid.
            if existing is not None:
                db.session.delete(notification_recipient)
        cls.query.filter(cls.recipient_id == old_account.id).update(
            {'recipient_id': new_account.id}, synchronize_session=False
        )


class NotificationFor(NotificationRecipientMixin):
    """View-only wrapper to mimic :class:`UserNotification`."""

    notification: Notification | PreviewNotification
    identity: Any = None
    read_at: Any = None
    revoked_at: Any = None
    is_revoked: bool = False
    is_read: bool = False

    views = Registry()

    def __init__(
        self, notification: Notification | PreviewNotification, recipient: Account
    ) -> None:
        self.notification = notification
        self.eventid = notification.eventid
        self.notification_id = notification.id

        self.recipient = recipient
        self.recipient_id = recipient.id

    @property
    def role(self) -> str | None:
        """User's primary matching role for this notification."""
        if self.document and self.recipient:
            roles = self.document.roles_for(self.recipient)
            for role in self.notification.roles:
                if role in roles:
                    return role
        return None

    def rolledup_fragments(self) -> Query | None:
        """Return a query to load the notification fragment."""
        if not self.notification.fragment_model:
            return None
        return self.notification.fragment_model.query.filter_by(
            uuid=self.notification.fragment_uuid
        )


# --- Notification preferences ---------------------------------------------------------


class NotificationPreferences(BaseMixin, Model):
    """Holds a user's preferences for a particular :class:`Notification` type."""

    __tablename__ = 'notification_preferences'

    #: Id of account whose preferences are represented here
    account_id: Mapped[int] = sa.orm.mapped_column(
        sa.Integer,
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    #: User account whose preferences are represented here
    account = with_roles(
        relationship(Account, back_populates='notification_preferences'),
        read={'owner'},
        grants={'owner'},
    )

    # Notification type, corresponding to Notification.type (a class attribute there)
    # notification_type = '' holds the veto switch to disable a transport entirely
    notification_type: Mapped[str] = immutable(
        sa.orm.mapped_column(sa.Unicode, nullable=False)
    )

    by_email: Mapped[bool] = with_roles(
        sa.orm.mapped_column(sa.Boolean, nullable=False), rw={'owner'}
    )
    by_sms: Mapped[bool] = with_roles(
        sa.orm.mapped_column(sa.Boolean, nullable=False), rw={'owner'}
    )
    by_webpush: Mapped[bool] = with_roles(
        sa.orm.mapped_column(sa.Boolean, nullable=False), rw={'owner'}
    )
    by_telegram: Mapped[bool] = with_roles(
        sa.orm.mapped_column(sa.Boolean, nullable=False), rw={'owner'}
    )
    by_whatsapp: Mapped[bool] = with_roles(
        sa.orm.mapped_column(sa.Boolean, nullable=False), rw={'owner'}
    )

    __table_args__ = (sa.UniqueConstraint('account_id', 'notification_type'),)

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
        if self.account:
            self.set_defaults()

    def __repr__(self) -> str:
        """Represent :class:`NotificationPreferences` as a string."""
        return (
            f'NotificationPreferences('
            f'notification_type={self.notification_type!r}, account={self.account!r}'
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
            if not self.account.notification_preferences:
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
                                for np in self.account.notification_preferences.values()
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
    def type_cls(self) -> type[Notification] | None:
        """Return the Notification subclass corresponding to self.notification_type."""
        # Use `registry.get(type)` instead of `registry[type]` because the user may have
        # saved preferences for a discontinued notification type. These should ideally
        # be dropped in migrations, but it's possible for the data to be outdated.
        return notification_type_registry.get(self.notification_type)

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        for ntype, prefs in list(old_account.notification_preferences.items()):
            if ntype in new_account.notification_preferences:
                db.session.delete(prefs)
        cls.query.filter(cls.account_id == old_account.id).update(
            {'account_id': new_account.id}, synchronize_session=False
        )

    @sa.orm.validates('notification_type')
    def _valid_notification_type(self, key: str, value: str | None) -> str:
        if value == '':  # Special-cased name for main preferences
            return value
        if value is None or value not in notification_type_registry:
            raise ValueError(f"Invalid notification_type: {value}")
        return value


@reopen(Account)
class __Account:
    all_notifications: DynamicMapped[NotificationRecipient] = with_roles(
        relationship(
            NotificationRecipient,
            lazy='dynamic',
            order_by=NotificationRecipient.created_at.desc(),
            viewonly=True,
        ),
        read={'owner'},
    )

    notification_preferences: Mapped[dict[str, NotificationPreferences]] = relationship(
        NotificationPreferences,
        collection_class=column_keyed_dict(NotificationPreferences.notification_type),
        back_populates='account',
    )

    # This relationship is wrapped in a property that creates it on first access
    _main_notification_preferences: Mapped[NotificationPreferences] = relationship(
        NotificationPreferences,
        primaryjoin=sa.and_(
            NotificationPreferences.account_id == Account.id,
            NotificationPreferences.notification_type == '',
        ),
        uselist=False,
        viewonly=True,
    )

    @cached_property
    def main_notification_preferences(self) -> NotificationPreferences:
        """Return user's main notification preferences, toggling transports on/off."""
        if not self._main_notification_preferences:
            main = NotificationPreferences(
                notification_type='',
                account=self,
                by_email=True,
                by_sms=True,
                by_webpush=False,
                by_telegram=False,
                by_whatsapp=True,
            )
            db.session.add(main)
            return main
        return self._main_notification_preferences


# --- Signal handlers ------------------------------------------------------------------


auto_init_default(Notification.eventid)


@event.listens_for(Notification, 'mapper_configured', propagate=True)
def _register_notification_types(mapper_: Any, cls: type[Notification]) -> None:
    # Don't register the base class itself, or inactive types
    if cls is not Notification:
        # Add the subclass to the registry

        if cls.document_model is None:
            raise TypeError(
                f"Notification subclass {cls!r} must specify document_model"
            )

        # Exclude inactive notifications in the registry. It is used to populate the
        # user's notification preferences screen.
        if cls.active and cls.cls_type == cls.pref_type:
            notification_type_registry[cls.cls_type] = cls
        # Include inactive notifications in the web types, as this is used for the web
        # feed of past notifications, including deprecated (therefore inactive) types
        if cls.allow_web:
            notification_web_types.add(cls.cls_type)
