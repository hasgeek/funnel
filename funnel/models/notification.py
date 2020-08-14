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

6. For each user in the filtered list, a UserNotification db instance is created. A
    scan is performed for previous instances of UserNotification referring to the
    same Update object, determined from UserNotification.notification.document_uuid,
    and those are revoked to remove them from the user's feed.

7. A separate view helper class named NewUpdateNotificationRenderView contains methods
    named `web`, `email`, `sms`, `webpush`, `telegram` and `whatsapp`. These may be
    called with the UserNotification instance as a parameter, and are expected to return
    a rendered message. The `web` render is used for the notifications page on the
    website.

8. Views are registered to the model, so the dispatch mechanism only needs to call
    ``user_notification.render.web()`` etc to get the rendered content. The dispatch
    mechanism then calls the appropriate transport helper (``send_email``, etc) to do
    the actual sending. The message id returned by these functions is saved to the
    messageid columns in UserNotification, as record that the notification was sent.
    If the transport doesn't support message ids, a random non-None value is used. When
    all available transports are sent, the `is_dispatched` column is set. This is used
    to prevent dupe sends from requeued background jobs.

9. The notifications endpoint on the website shows a feed of UserNotification items and
    handles the ability to mark each as read. This marking is also automatically
    performed in the links in the rendered templates that were sent out.

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
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.collections import column_mapped_collection

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import auto_init_default, with_roles
from coaster.utils import LabeledEnum, classmethodproperty

from . import BaseMixin, NoIdMixin, UUIDType, db
from .user import User

__all__ = [
    'Notification',
    'NotificationPreferences',
    'SMSMessage',
    'SMS_STATUS',
    'UserNotification',
    'notification_type_registry',
]

# --- Registries -----------------------------------------------------------------------

#: Registry of Notification subclasses, automatically populated
notification_type_registry = {}

# --- Flags ----------------------------------------------------------------------------


class SMS_STATUS(LabeledEnum):  # NOQA: N801
    QUEUED = (0, __("Queued"))
    PENDING = (1, __("Pending"))
    DELIVERED = (2, __("Delivered"))
    FAILED = (3, __("Failed"))
    UNKNOWN = (4, __("Unknown"))


class NOTIFICATION_CATEGORY(LabeledEnum):  # NOQA: N801
    NONE = (0, __("Uncategorized"))
    ACCOUNT = (1, __("My account"))
    SUBSCRIPTIONS = (2, __("My subscriptions and billing"))
    PARTICIPANT = (3, __("Projects I am participating in"))
    PROJECT_CREW = (4, __("Projects I am a collaborator in"))


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
    document and target.
    """

    __tablename__ = 'notification'

    #: Random identifier for the event that triggered this notification. Event ids can
    #: be shared across notifications, and will be used to enforce a limit of one
    #: instance of a UserNotification per-event rather than per-notification.
    eventid = db.Column(
        UUIDType(binary=False), primary_key=True, nullable=False, default=uuid4
    )

    #: Notification id
    id = db.Column(  # NOQA: A003
        UUIDType(binary=False), primary_key=True, nullable=False, default=uuid4
    )

    category = NOTIFICATION_CATEGORY.NONE
    description = __("Unspecified notification type")

    #: Subclasses may set this to aid loading of :attr:`document`
    document_model = None

    #: Subclasses may set this to aid loading of :attr:`target`
    target_model = None

    #: Roles to send notifications to. Roles must be in order of priority for situations
    #: where a user has more than one role on the document.
    roles = []

    #: The preference context this notification is being served under. Users may have
    #: customized preferences per profile or project.
    preference_context = None

    #: Notification type (identifier for subclass of :class:`NotificationType`)
    type = db.Column(db.Unicode, nullable=False)  # NOQA: A003

    #: UUID of document that the notification refers to
    document_uuid = db.Column(UUIDType(binary=False), nullable=False, index=True)

    #: Optional target within document that the notification refers to. This may be the
    #: document itself, or something within it, such as a comment. Notifications for
    #: multiple targets are collapsed into a single notification.
    target_uuid = db.Column(UUIDType(binary=False), nullable=True)

    __mapper_args__ = {'polymorphic_on': type, 'with_polymorphic': '*'}

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

    renderers = {}  # Registry of {cls_type: CustomNotificationView}

    def __init__(self, document=None, target=None, **kwargs):
        if document:
            kwargs['document_uuid'] = document.uuid
        if target:
            kwargs['target_uuid'] = target.uuid
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

    @cached_property
    def target(self):
        """
        Retrieve the target within a document referenced by this Notification, if any.

        This assumes the underlying object won't disappear, as there is no SQL foreign
        key constraint enforcing a link.
        """
        if self.target_model and self.target_uuid:
            return self.target_model.query.filter_by(uuid=self.target_uuid).one()

    def renderer(self, cls):
        """
        Decorator for view class containing render methods.

        Usage in views::

            from ..models import MyNotificationType
            from .views import NotificationView

            @MyNotificationType.renderer
            class MyNotificationView(NotificationView):
                ...
        """
        self.renderers[self.cls_type] = cls
        return cls

    def user_preferences(self, user):
        """Return notification preferences for the user"""
        prefs = user.notification_preferences.get(self.type)
        if not prefs:
            prefs = NotificationPreferences(user=user, type=self.type)
            db.session.add(prefs)
            user.notification_preferences[self.type] = prefs
        return prefs

    def dispatch(self):
        """
        Create UserNotification instances and yield in an iterator.

        This is a heavy method and must be called from a background job. When making
        new notifications, it will revoke previous notifications issued against the
        same document.

        Subclasses wanting more control over how their notifications are dispatched
        should override this method.
        """
        for (user, role) in (self.target or self.document).actors_with(
            self.roles, with_role=True
        ):
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


class UserNotification(NoIdMixin, db.Model):
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
    user = with_roles(db.relationship(User), read={'owner'}, grants={'owner'},)

    #: Random eventid, shared with the Notification instance
    eventid = db.Column(UUIDType(binary=False), primary_key=True, nullable=False)

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

    #: Whether the notification has been dispatched. This should be used in conjunction
    #: with per-transport transaction id columns to avoid repeat sending.
    is_dispatched = with_roles(
        db.Column(db.Boolean, default=False, nullable=False), read={'owner'}
    )

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
            [eventid, notification_id], [Notification.eventid, Notification.id]
        ),
    )

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

    with_roles(is_read, read={'owner'}, write={'owner'})

    @with_roles(read={'owner'})
    @property
    def document(self):
        """The document that this notification is for."""
        return self.notification.document

    @with_roles(read={'owner'})
    @property
    def target(self):
        """The target within this document that this notification is for."""
        return self.notification.target

    def user_preferences(self):
        """Return the user's notification preferences."""
        return self.notification.user_preferences(self.user)

    def transports(self):
        """
        Return transport addresses for each transport.

        Uses three criteria:

        1. The notification type allows delivery over this transport
        2. The user preference allows it
        2. The user has this transport (verified email or phone, etc)
        """
        transports = SimpleNamespace(
            email=None, sms=None, webpush=None, telegram=None, whatsapp=None
        )
        user_prefs = self.user_preferences()
        if self.notification.allow_email and user_prefs.by_email:
            transports.email = self.user.transport_for_email(
                self.notification.preference_context
            )
        if self.notification.allow_sms and user_prefs.by_sms:
            transports.sms = self.user.transport_for_sms(
                self.notification.preference_context
            )
        if self.notification.allow_webpush and user_prefs.by_webpush:
            transports.webpush = self.user.transport_for_webpush(
                self.notification.preference_context
            )
        if self.notification.allow_telegram and user_prefs.by_telegram:
            transports.telegram = self.user.transport_for_telegram(
                self.notification.preference_context
            )
        if self.notification.allow_whatsapp and user_prefs.by_whatsapp:
            transports.whatsapp = self.user.transport_for_whatsapp(
                self.notification.preference_context
            )
        return transports

    def _revoke(self):
        """Revoke this instance and return the referred target."""
        self.is_revoked = True
        return self.target

    def revoke_previous(self):
        """
        Find previous instances of notifications against the same document and revoke
        them, returning their targets.
        """
        query = UserNotification.query.join(Notification)
        if self.notification.target_model:
            query = query.join(
                self.notification.target_model,
                UserNotification.target_uuid == self.notification.target_model.uuid,
            )
        targets = {
            user_notification._revoke()
            for user_notification in query.filter(
                UserNotification.user_id == self.user_id,  # This user
                Notification.id != self.notification_id,  # But not this notification
                Notification.type == self.notification.type,
                Notification.document_uuid == self.notification.document_uuid,
            ).order_by(UserNotification.created_at.desc())
        }
        if None in targets:
            targets.remove(None)
        return targets

    def rollup_notifications(self):
        """Return all existing notifications of the same type on this document"""
        return (
            UserNotification.query.join(Notification)
            .filter(
                UserNotification.user_id == self.user_id,
                Notification.type == self.notification.type,
                Notification.document_uuid == self.notification.document_uuid,
            )
            .order_by(UserNotification.created_at.desc())
        )

    def dispatch(self):
        """Perform a dispatch using the notification type's view renderer."""
        return Notification.renderers[self.notification.cls_type](
            self.notification
        ).dispatch(self)

    def render(self):
        """Render for the web, using the notification type's view renderer."""
        return Notification.renderers[self.notification.cls_type](
            self.notification
        ).web(self)

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


User.notifications = with_roles(
    db.relationship(
        UserNotification, lazy='dynamic', order_by=UserNotification.created_at.desc()
    ),
    read={'owner'},
)

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
    # To consider: type = '' holds the veto switch to disable a transport entirely
    notification_type = db.Column(db.Unicode, nullable=False)

    by_email = db.Column(db.Boolean, nullable=False)
    by_sms = db.Column(db.Boolean, nullable=False)
    by_webpush = db.Column(db.Boolean, nullable=False)
    by_telegram = db.Column(db.Boolean, nullable=False)
    by_whatsapp = db.Column(db.Boolean, nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'notification_type'),)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.user:
            self.set_defaults()

    def set_defaults(self):
        """
        Set defaults based on whether the user has it enabled for other notifications.
        """
        transport_attrs = (
            'by_email',
            'by_sms',
            'by_webpush',
            'by_telegram',
            'by_whatsapp',
        )
        if not self.user.notification_preferences:
            for attr in transport_attrs:
                if getattr(self, attr) is None:
                    # Default True if this is the first notification
                    setattr(self, attr, True)
        else:
            for attr in transport_attrs:
                if getattr(self, attr) is None:
                    # If this transport is enabled for any existing notification type,
                    # also enable here.
                    setattr(
                        self,
                        attr,
                        any(
                            getattr(np, attr)
                            for np in self.user.notification_preferences.values()
                        ),
                    )

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
        if value not in notification_type_registry:
            raise ValueError("Invalid notification_type: %s" % value)
        return value


User.notification_preferences = db.relationship(
    NotificationPreferences,
    collection_class=column_mapped_collection(
        NotificationPreferences.notification_type
    ),
)


# --- Signal handlers ------------------------------------------------------------------


auto_init_default(Notification.eventid)


@event.listens_for(Notification, 'mapper_configured', propagate=True)
def _register_notification_types(mapper_, cls):
    if cls is not Notification:  # Don't register the base class itself
        notification_type_registry[cls.__mapper_args__['polymorphic_identity']] = cls
