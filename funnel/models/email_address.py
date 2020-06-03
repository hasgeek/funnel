from typing import Optional
import hashlib

from sqlalchemy import event, inspect
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.attributes import NEVER_SET, NO_VALUE

from werkzeug.utils import cached_property

from coaster.sqlalchemy import ImmutableColumnError, immutable
from coaster.utils import LabeledEnum, require_one_of

from ..signals import email_address_activity
from . import BaseMixin, db

__all__ = ['EMAIL_DELIVERY_STATE', 'EmailAddress']


class EMAIL_DELIVERY_STATE(LabeledEnum):  # NOQA: N801
    """
    Email delivery states. Use ``dict(EMAIL_DELIVERY_STATE)`` to get contents.

    The 'active' state here is used to distinguish from an abandoned mailbox that
    continues to receive messages, or one that drops them without reporting a bounce.
    For example, email delivery to the spam folder will appear normal but not active.
    The 'active' state is not a reliable indicator the activity of a recipient, which
    requires tracking per email message sent.

    The bounce states require supporting infrastructure to record bounce reports from
    the email server. Active state requires incoming link handlers to report activity.
    """

    UNKNOWN = (0, 'unknown')  # Never mailed
    NORMAL = (1, 'normal')  # Mail sent, nothing further known
    ACTIVE = (2, 'active')  # Recipient is interacting with received messages
    SOFT_BOUNCE = (3, 'soft_bounce')  # Soft bounce reported
    HARD_BOUNCE = (4, 'hard_bounce')  # Hard bounce reported


def make_email_canonical(email: str) -> str:
    """
    Construct a canonical representation of the email address.

    Used by :meth:`email_canonical` and :meth:`new`
    """
    mailbox, domain = email.lower().split('@', 1)
    if '+' in mailbox:
        mailbox = mailbox[: mailbox.find('+')]
    return f'{mailbox}@{domain}'


def make_email_sha256(email: str) -> str:
    """
    Returns an SHA256 hash of the given email address, with an added prefix.

    The hardcoded `mailto:` prefix functions as a fixed salt, reducing the utility of
    pre-existing rainbow tables of the plain email addresses. However, it does nothing
    for tables constructed with the same prefix. We depend on this prefix being
    unusual for such tables.
    """
    return hashlib.sha256(('mailto:' + email).encode('utf-8')).hexdigest()


class EmailAddress(BaseMixin, db.Model):
    """
    Represents an email address as a standalone entity, with associated metadata.

    Also supports the notion of a forgotten email address, holding a placeholder for it
    using a hash of the email address, to prevent accidental rememberance by replay.
    Use cases include unsubscription, where we don't want to store the email address,
    while also being able to identify that it was unsubscribed.

    New email addresses must be added using the :meth:`add` classmethod.
    """

    __tablename__ = 'email_address'

    #: The email address, centrepiece of this model. Case preserving.
    email = db.Column(db.Unicode(254), nullable=True)

    # email_lower is defined below

    #: SHA256 hash of :property:`email_lower`. Kept permanently even if email is removed
    sha256 = immutable(db.Column(db.Unicode(64), nullable=False, unique=True))

    #: SHA256 hash of :property:`email_canonical`. Kept permanently for blacklist
    #: detection. Indexed but does not use a unique constraint because a+b@tld and
    #: a+c@tld are both a@tld canonically.
    sha256_canonical = immutable(db.Column(db.Unicode(64), nullable=False, index=True))

    #: Does this email address work?
    delivery_state = db.Column(
        db.Integer, nullable=False, default=EMAIL_DELIVERY_STATE.UNKNOWN
    )
    #: Timestamp of last known delivery state
    delivery_state_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )

    #: Is this email address blocked from being used? If so, email should be null
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.Index(
            'ix_email_address_email_lower',
            db.func.lower(email).label('email_lower'),
            unique=True,
            postgresql_ops={'email_lower': 'varchar_pattern_ops'},
        ),
        db.CheckConstraint(
            db.and_(email.isnot(None), is_blocked.isnot(True)),
            'email_address_email_is_blocked_check',
        ),
        db.CheckConstraint(delivery_state.in_(EMAIL_DELIVERY_STATE.keys())),
    )

    @cached_property
    def md5(self) -> Optional[str]:
        """
        MD5 hash of :attr:`email_lower`, for legacy use only.
        """
        return (
            hashlib.md5(  # NOQA: S303 # skipcq: PTC-W1003 # nosec
                self.email_lower.encode()
            ).hexdigest()
            if self.email_lower
            else None
        )

    @hybrid_property
    def email_lower(self) -> Optional[str]:
        """
        Lowercase representation of the email address.

        Is expected to be unique, but does not block reuse of the same mailbox using
        the ``+suffix`` method (see :attr:`email_canonical`), nor is it capable of
        detecting aliases defined by the recipient's email server.
        """
        # Note: Python lower() is not guaranteed identical to SQL lower(),
        # although that is extremely unlikely with the ASCII character set of an
        # email address.
        return self.email.lower() if self.email else None

    @email_lower.expression
    def email_lower(self):  # TODO: Type hint
        return db.func.lower(self.email)  # SQL lower() can handle email being null

    @cached_property
    def email_canonical(self) -> Optional[str]:
        """
        Email address with the ``+suffix`` portion of the mailbox removed.

        This is only used to identify and prevent re-use of blacklisted email addresses
        using the ``+suffix`` method. Regular use does allow the ``+`` symbol.

        The canonical representation is not stored, but its sha256 representation is
        """
        return make_email_canonical(self.email) if self.email else None

    def __str__(self) -> str:
        """Cast email address into a string."""
        return str(self.email or '')

    def __repr__(self) -> str:
        """Debugging representation of the email address."""
        return f'EmailAddress({self.email!r})'

    def __init__(self, email: str) -> None:
        self.email = email
        self.sha256 = make_email_sha256(self.email_lower)
        self.sha256_canonical = make_email_sha256(self.email_canonical)

    def mark_sent(self) -> None:
        """Record fact of an email message being sent to this address."""
        self.delivery_state = EMAIL_DELIVERY_STATE.NORMAL
        self.delivery_state_at = db.func.utcnow()
        email_address_activity.send(self)

    def mark_active(self) -> None:
        """Record fact of recipient activity."""
        self.delivery_state = EMAIL_DELIVERY_STATE.ACTIVE
        self.delivery_state_at = db.func.utcnow()
        email_address_activity.send(self)

    def mark_soft_bounce(self) -> None:
        """Record fact of a soft bounce to this email address."""
        self.delivery_state = EMAIL_DELIVERY_STATE.SOFT_BOUNCE
        self.delivery_state_at = db.func.utcnow()
        email_address_activity.send(self)

    def mark_hard_bounce(self) -> None:
        """Record fact of a soft bounce to this email address."""
        self.delivery_state = EMAIL_DELIVERY_STATE.HARD_BOUNCE
        self.delivery_state_at = db.func.utcnow()
        email_address_activity.send(self)

    def mark_forgotten(self) -> None:
        """Forget an email address by blanking out email column."""
        self.email = None

    @classmethod
    def get(
        cls,
        email: Optional[str] = None,
        sha256: Optional[str] = None,
        sha256_canonical: Optional[str] = None,
    ) -> 'Optional(EmailAddress)':
        """
        Get an :class:`EmailAddress` instance using any one of the indexed columns.

        The current implementation adds a fixed salt to sha256 columns. The input
        parameter must be made using the same salt.
        """
        require_one_of(email=email, sha256=sha256, sha256_canonical=sha256_canonical)
        if email:
            return cls.query.filter_by(email_lower=db.func.lower(email)).one_or_none()
        elif sha256:
            return cls.query.filter_by(sha256=sha256).one_or_none()
        elif sha256_canonical:
            return cls.query.filter_by(sha256_canonical=sha256_canonical).one_or_none()

    @classmethod
    def add(cls, email: str) -> 'EmailAddress':
        """
        Create a new :class:`EmailAddress` after validation.

        Raises an exception if not available.
        """
        pass  # TODO

    @classmethod
    def add_for(cls, user: 'User', email: str) -> 'EmailAddress':
        """
        Create a new :class:`EmailAddress` after validation.

        Unlike :meth:`add`, this one requires the email address to not be claimed by
        an existing user via a UserEmail record.
        """
        pass  # TODO

    # TODO: validate_for that's like add_for minus the adding, for form validation

    # TODO: Blacklisted state marker and transition
    # TODO: user_bound_via = relationship(UserEmail), defined as a backref from there,
    # and user_bound_to as an association_proxy to User model

    @classmethod
    def validate_for(cls, user: 'User', email: str) -> Optional[str]:
        """
        Validate whether the specified email address is available to the specified user.

        Returns None if available or a string describing the concern if not. Possible
        return values:

        1. 'assigned' indicating it has been assigned to another user
        1. 'blocked' indicating it h
        2. 'soft_bounce'
        """


@event.listens_for(EmailAddress.email, 'set')
def _validate_email(target, value, old_value, initiator):
    # First: check if the email attribute can be set
    if old_value == value:
        # Old value is new value. Do nothing. Return without validating
        return
    elif old_value is NEVER_SET:
        # Old value was never set. Allow validation to continue
        pass
    elif old_value is NO_VALUE and inspect(target).has_identity is False:
        # Old value is unknown and target is a transient object. Continue
        pass
    elif value is None:
        # Caller is trying to unset email. Allow this
        pass
    elif old_value is None:
        # Caller is trying to restore email. Allow but validate match for sha256
        pass
    else:
        # Under any other condition, email is immutable
        raise ImmutableColumnError('EmailAddress', 'email', old_value, value)

    # All clear? Now check what we have
    if value is not None:
        hashed = make_email_sha256(value.lower())
        if hashed != target.sha256:
            raise ValueError("Email address does not match existing sha256 hash")
    # We don't have to set target.email because SQLAlchemy will do that for us


# --- Tail imports ---------------------------------------------------------------------
from .user import User  # isort:skip
