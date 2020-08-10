"""
Notification primitives.

Notification models and support classes for implementing notifications, best understood
using examples:

Scenario: Project P's editor E posts an update U
Where: User A is a participant on the project
Result: User A receives a notification about a new update on the project

How it works:

1. View handler that creates the Update triggers an UpdateNotification on it. This is
   an instance of NotificationType. It is not a db model. The UpdateNotification class
   has templates for delivering to various roles using various mediums. It may also
   specify how each role can respond to the notification (future use, for "Mark read",
   "Reply", etc).

2. Roles? Yes. UpdateNotification says it should be delivered to users possessing the
   roles 'project_crew' and 'project_participant' on the Update object, in that order.
   That means a user who is both crew and participant will only get the version meant
   for crew members and won't be notified twice. Versions will have minor differences
   such as in language: "the project you're a crew member of had an update", versus
   "the project you're a participant of had an update".

3. A Notification instance is created referring to the UpdateNotification type and
   Update model. This is a db model, but is designed to be discardable after a threshold
   time period, from a few days to a few months.

4. The Update model declares that user lists are maintained by the Project model
   and not itself. The notification flow depends on this to determine how to proceed.

5. To find users with the required roles, `Update.actors_for({roles})` is called. The
   default implementation in RoleMixin is aware that these roles are inherited from
   Project (using granted_via declarations), and so calls `Update.project.actors_for`.
   These users are sent to Project's send_notifications method (inherited from
   NotificationSubscriptionMixin),

6. User preferences are obtained from the User model (media to deliver over), the
   Profile model (email address to use; forthcoming), maybe Rsvp model (whether the user
   wants updates for this project) and a filtered list of users is created, with links
   to change their preferences (unsubscribe, manage preferences).

7. For each user in the filtered list, a UserNotification db instance is created. A
   scan is performed for previous instances of UserNotification referring to the
   same Update object, determined from UserNotification.notification.document_uuid,
   and those are revoked to remove them from the user's feed.

8. The combination of UpdateNotification type + UserNotification object produces
   rendered templates that are dispatched to that particular user over each medium
   (email, SMS, web push, etc).

9. The `/updates` endpoint on the website shows a feed of UserNotification items and
   handles the ability to mark each as read. This marking is also automatically
   performed in the links in the rendered templates that were sent out.

Steps 5-7 may need optimization as it's generally better to produce a target list in one
shot instead of making a larger list and then filtering from it in-app.
"""

from werkzeug.utils import cached_property

from baseframe import __
from coaster.utils import LabeledEnum

from . import BaseMixin, NoIdMixin, UuidMixin, UUIDType, db
from .user import User

__all__ = ['SMSMessage', 'SMS_STATUS']


# --- Flags ----------------------------------------------------------------------------


class SMS_STATUS(LabeledEnum):  # NOQA: N801
    QUEUED = (0, __("Queued"))
    PENDING = (1, __("Pending"))
    DELIVERED = (2, __("Delivered"))
    FAILED = (3, __("Failed"))
    UNKNOWN = (4, __("Unknown"))


# --- Models ---------------------------------------------------------------------------


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


class Notification(UuidMixin, BaseMixin, db.Model):
    """
    Holds a single notification for an activity on a document object.

    Notifications are fanned out to recipients using :class:`UserNotification` and
    may be accessed through the website and delivered over email, push notification, SMS
    or other media.
    """

    __tablename__ = 'notification'
    __uuid_primary_key__ = True

    #: Notification type (identifier for subclass of :class:`NotificationType`)
    type = db.Column(db.Unicode, nullable=False)  # NOQA: A003

    #: Type of document that the notification refers to (id is cls.__tablename__)
    document_type = db.Column(db.Unicode, nullable=False)
    #: UUID of document that the notification refers to
    document_uuid = db.Column(UUIDType(binary=False))

    #: Target within document that the notification refers to. This may be the
    #: document itself, or something within it, such as a comment. Notifications for
    #: multiple targets are collapsed into a single notification.
    target_type = db.Column(db.Unicode, nullable=False)
    target_uuid = db.Column(UUIDType(binary=False))

    #: Ordered list of roles who must receive the notification (space separated)
    #:
    _ordered_roles = db.Column('ordered_roles', db.Unicode, nullable=False)

    __mapper_args__ = {'polymorphic_on': type}

    @property
    def ordered_roles(self):
        return self._ordered_roles.split()

    @ordered_roles.setter
    def ordered_roles(self, value):
        self._ordered_roles = ' '.join(value)

    @cached_property
    def document(self):
        return self._document


class UserNotification(NoIdMixin):
    """
    The recipient of a notification.
    """

    __tablename__ = 'notification_recipient'

    #: Id of notification that this user received
    notification_id = db.Column(
        None,
        db.ForeignKey('notification.id', ondelete='CASCADE'),
        primary_key=True,
        nullable=False,
    )
    #: Notification that this user received
    notification = db.relationship(
        Notification, backref=db.backref('recipients', lazy='dynamic')
    )

    #: Id of user being notified
    user_id = db.Column(
        None,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
        nullable=False,
        index=True,
    )
    #: User being notified
    user = db.relationship(User, backref=db.backref('notifications', lazy='dynamic'))

    #: Whether the notification has been read
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    #: Whether the notification has been revoked. This can happen if:
    #: 1. The action that caused the notification has been undone (future use), or
    #: 2. A new notification has been raised for the same document and this user was
    #:    a recipient of thee new notification.
    is_revoked = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # TODO: Columns for transaction ids by delivery medium
