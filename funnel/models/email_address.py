from __future__ import annotations

from typing import Iterable, List, Optional
import hashlib

from sqlalchemy import event, inspect
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.attributes import NO_VALUE

from werkzeug.utils import cached_property

from pyisemail import is_email
import base58

from coaster.sqlalchemy import StateManager, auto_init_default, immutable, with_roles
from coaster.utils import LabeledEnum, require_one_of

from . import BaseMixin, db

__all__ = [
    'EMAIL_DELIVERY_STATE',
    'EmailAddressError',
    'EmailAddressBlockedError',
    'EmailAddressInUseError',
    'EmailAddress',
    'EmailAddressMixin',
]


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


def canonical_email_representation(email: str) -> List[str]:
    """
    Construct canonical representations of the email address, for deduplication.

    Used by :meth:`EmailAddress.email_canonical` and :meth:`EmailAddress.add`.

    A more comprehensive implementation is available in the mxsniff library.
    Unfortunately, that is not guaranteed stable long term as it generates canonical
    representations from an unversioned living database of known email providers. This
    implementation versions the provider-specific rules to return representations before
    and after the change.

    One specific example is Gmail's well known policy of ignoring periods in the mailbox
    portion of @gmail.com addresses. It is replicated here because Gmail is a very large
    provider. Two representations are returned in this case, with and without these
    specific rules.

    This function strips sub-addresses using the ``+address`` syntax and assumes all
    email addresses are lowercase. These are practical considerations and not based on
    a strict reading of the ``addr-spec`` in RFC 5322/2822.

    The canonical representation of an email address is not suitable for emailing. It is
    only usable for comparison, directly or via hashes.
    """
    mailbox, domain = email.lower().split('@', 1)
    if '+' in mailbox:
        mailbox = mailbox[: mailbox.find('+')]

    representations = [f'{mailbox}@{domain}']

    # Hardcode for Gmail's special cases owing to its popularity
    if domain == 'googlemail.com':
        domain = 'gmail.com'
    if domain == 'gmail.com':
        if '.' in mailbox:
            mailbox = mailbox.replace('.', '')
        gmail_representation = f'{mailbox}@{domain}'
        if gmail_representation != representations[0]:
            # Gmail special case should take priority
            representations.insert(0, gmail_representation)

    return representations


def email_blake2b160_hash(email: str) -> bytes:
    """
    Returns an BLAKE2b hash of the given email address using digest size 20 (160 bits).
    Caller is responsible for lowercasing if necessary.
    """
    return hashlib.blake2b(email.encode('utf-8'), digest_size=20).digest()


class EmailAddressError(Exception):
    """Base class for EmailAddress exceptions"""


class EmailAddressBlockedError(EmailAddressError):
    """Email address is blocked from use"""


class EmailAddressInUseError(EmailAddressError):
    """Email address is in use by another actor"""


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

    #: Backrefs to this model from other models, populated by :class:`EmailAddressMixin`
    __backrefs__ = set()
    #: These backrefs claim exclusive use of the email address for their linked actor
    __exclusive_backrefs__ = set()

    #: The email address, centrepiece of this model. Case preserving.
    #: Validated by the :func:`_validate_email` event handler
    email = db.Column(db.Unicode, nullable=True)

    # email_lower is defined below

    #: BLAKE2b 160-bit hash of :property:`email_lower`. Kept permanently even if email
    #: is removed. SQLAlchemy type LargeBinary maps to PostgreSQL BYTEA. Despite the
    #: name, we're only storing 20 bytes
    blake2b160 = immutable(db.Column(db.LargeBinary, nullable=False, unique=True))

    #: BLAKE2b 160-bit hash of :property:`email_canonical`. Kept permanently for blocked
    #: email detection. Indexed but does not use a unique constraint because a+b@tld and
    #: a+c@tld are both a@tld canonically.
    blake2b160_canonical = immutable(
        db.Column(db.LargeBinary, nullable=False, index=True)
    )

    #: Does this email address work? Records last known delivery state
    _delivery_state = db.Column(
        'delivery_state',
        db.Integer,
        StateManager.check_constraint('delivery_state', EMAIL_DELIVERY_STATE),
        nullable=False,
        default=EMAIL_DELIVERY_STATE.UNKNOWN,
    )
    delivery_state = StateManager(
        '_delivery_state',
        EMAIL_DELIVERY_STATE,
        doc="Last known delivery state of this email address",
    )
    #: Timestamp of last known delivery state
    delivery_state_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )

    #: Is this email address blocked from being used? If so, :attr:`email` should be
    #: null. Blocks apply to the canonical address (without the +sub-address variation),
    #: so a test for whether an address is blocked should use blake2b160_canonical to
    #: load the record. Other records with the same canonical hash _may_ exist without
    #: setting the flag due to a lack of database-side enforcement.
    _is_blocked = db.Column('is_blocked', db.Boolean, nullable=False, default=False)

    __table_args__ = (
        # TODO: Reconsider this. Blocking and forgetting are distinct concerns.
        db.CheckConstraint(
            db.or_(
                _is_blocked.isnot(True),
                db.and_(_is_blocked.is_(True), email.is_(None),),
            ),
            'email_address_email_is_blocked_check',
        ),
    )

    @hybrid_property
    def is_blocked(self):
        """"
        Read-only flag indicating this email address is blocked from use. To set this
        flag, call :classmethod:`mark_blocked` using the email address. The flag will be
        simultaneously set on all matching instances.
        """
        return self._is_blocked

    # This should not use `cached_property` as email is partially mutable
    @property
    def email_lower(self) -> Optional[str]:
        """
        Lowercase representation of the email address.
        """
        return self.email.lower() if self.email else None

    # This should not use `cached_property` as email is partially mutable
    @property
    def email_canonical(self) -> Optional[str]:
        """
        Email address with the ``+sub-address`` portion of the mailbox removed.

        This is only used to identify and prevent re-use of blocked email addresses
        using the ``+sub-address`` method. Regular use does allow the ``+`` symbol.
        Special handling for the gmail.com domain also strips periods from the
        canonical representation. This makes the representation invalid for emailing.

        The canonical representation is not stored, but its blake2b160 representation is
        """
        return canonical_email_representation(self.email)[0] if self.email else None

    @with_roles(read={'all'})
    @cached_property
    def email_hash(self) -> str:
        """Public identifier string for email address, usable in URLs."""
        return base58.b58encode(self.blake2b160).decode()

    @with_roles(call={'all'})
    def md5(self) -> Optional[str]:
        """MD5 hash of :property:`email_lower`, for legacy use only."""
        return (
            hashlib.md5(  # NOQA: S303 # skipcq: PTC-W1003 # nosec
                self.email_lower.encode('utf-8')
            ).hexdigest()
            if self.email_lower
            else None
        )

    def __str__(self) -> str:
        """Cast email address into a string."""
        return str(self.email or '')

    def __repr__(self) -> str:
        """Debugging representation of the email address."""
        return f'EmailAddress({self.email!r})'

    def __init__(self, email: str) -> None:
        if not isinstance(email, str):
            raise ValueError("A string email address is required")
        # Set the hash first so the email column validator passes. Both hash columns
        # are immutable once set, so there are no content validators for them.
        self.blake2b160 = email_blake2b160_hash(email.lower())
        self.email = email
        self.blake2b160_canonical = email_blake2b160_hash(self.email_canonical)

    @delivery_state.transition(None, delivery_state.NORMAL)
    def mark_sent(self) -> None:
        """Record fact of an email message being sent to this address."""
        self.delivery_state_at = db.func.utcnow()

    @delivery_state.transition(None, delivery_state.ACTIVE)
    def mark_active(self) -> None:
        """Record fact of recipient activity."""
        self.delivery_state_at = db.func.utcnow()

    @delivery_state.transition(None, delivery_state.SOFT_BOUNCE)
    def mark_soft_bounce(self) -> None:
        """Record fact of a soft bounce to this email address."""
        self.delivery_state_at = db.func.utcnow()

    @delivery_state.transition(None, delivery_state.HARD_BOUNCE)
    def mark_hard_bounce(self) -> None:
        """Record fact of a soft bounce to this email address."""
        self.delivery_state_at = db.func.utcnow()

    def refcount(self) -> int:
        """Returns count of references to this EmailAddress instance"""
        return sum(
            len(getattr(self, backref_name)) for backref_name in self.__backrefs__
        )

    @classmethod
    def mark_blocked(cls, email: str) -> None:
        """
        Mark email address as blocked.

        Looks up all existing instances of EmailAddress with the same canonical
        representation and amends them to forget the email address and set the
        :attr:`is_blocked` flag.
        """
        for obj in cls.get_canonical(email, is_blocked=False).all():
            # TODO: Reconsider forgetting. Blocking and forgetting are distinct
            # concerns. This makes a block irreversible as instances will have differing
            # sub-addresses. `mark_blocked_and_forgotten` should be a distinct method
            obj.email = None
            obj._is_blocked = True

    @classmethod
    def get(
        cls,
        email: Optional[str] = None,
        blake2b160: Optional[bytes] = None,
        email_hash: Optional[str] = None,
    ) -> Optional[EmailAddress]:
        """
        Get an :class:`EmailAddress` instance by email address or its hash.

        Internally converts an email-based lookup into a hash-based lookup.
        """
        require_one_of(email=email, blake2b160=blake2b160, email_hash=email_hash)
        if email:
            blake2b160 = email_blake2b160_hash(email.lower())
        elif email_hash:
            blake2b160 = base58.b58decode(email_hash)

        return cls.query.filter_by(blake2b160=blake2b160).one_or_none()

    @classmethod
    def get_canonical(
        cls, email: str, is_blocked: Optional[bool] = None
    ) -> Iterable[EmailAddress]:
        """
        Get :class:`EmailAddress` instances matching the canonical representation.

        Optionally filtered by the :attr:`is_blocked` flag.
        """
        hashes = [
            email_blake2b160_hash(result)
            for result in canonical_email_representation(email.lower())
        ]
        query = cls.query.filter(cls.blake2b160_canonical.in_(hashes))
        if is_blocked is not None:
            query = query.filter_by(_is_blocked=is_blocked)
        return query

    @classmethod
    def _get_existing(cls, email: str) -> Optional[EmailAddress]:
        """Internal method used by :meth:`add` and :meth:`add_for`"""
        with db.session.no_autoflush:
            if cls.get_canonical(email, is_blocked=True).notempty():
                raise EmailAddressBlockedError("Email address is blocked")
            return EmailAddress.get(email)

    @classmethod
    def add(cls, email: str) -> EmailAddress:
        """
        Create a new :class:`EmailAddress` after validation.

        Raises an exception if the address is blocked from use or the email address
        is syntactically invalid.

        This method will not flush the session before querying the database, to avoid
        flushing unrelated transient objects. Caller is responsible for ensuring edits
        to other :class:`EmailAddress` instances have been flushed or committed.
        """
        existing = cls._get_existing(email)
        if existing:
            existing.email = email
            return existing
        new_email = EmailAddress(email)
        db.session.add(new_email)
        return new_email

    @classmethod
    def add_for(cls, actor: User, email: str) -> EmailAddress:
        """
        Create a new :class:`EmailAddress` after validation.

        Unlike :meth:`add`, this one requires the email address to not be in an
        exclusive relationship with another user.

        This method will not flush the session before querying the database, to avoid
        flushing unrelated transient objects. Caller is responsible for ensuring edits
        to other :class:`EmailAddress` instances have been flushed or committed.
        """
        existing = cls._get_existing(email)
        if existing:
            for backref_name in EmailAddress.__exclusive_backrefs__:
                for related_obj in getattr(existing, backref_name):
                    user = getattr(related_obj, related_obj.__email_for__)
                    if user is not None and user != actor:
                        raise EmailAddressInUseError("This email address is in use")
            # No exclusive lock found? Let it be used then
            existing.email = email
            return existing
        new_email = EmailAddress(email)
        db.session.add(new_email)
        return new_email

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
        # TODO


class EmailAddressMixin:
    """Mixin class for models that refer to EmailAddress"""

    #: This class has an optional dependency on EmailAddress
    __email_optional__ = True
    #: This class has a unique constraint on the fkey to EmailAddress
    __email_unique__ = False
    #: A relationship from this model is for the (single) actor at this attr
    __email_for__ = None
    #: If `__email_for__` is specified and this flag is True, the email address is
    #: considered exclusive to this user and may not be used by any other user
    __email_is_exclusive__ = False

    @declared_attr
    def email_address_id(cls):
        return db.Column(
            None,
            db.ForeignKey('email_address.id', ondelete='SET NULL'),
            nullable=cls.__email_optional__,
            unique=cls.__email_unique__,
            index=not cls.__email_unique__,
        )

    @declared_attr
    def email_address(cls):
        backref_name = 'used_in_' + cls.__tablename__
        EmailAddress.__backrefs__.add(backref_name)
        if cls.__email_for__ and cls.__email_is_exclusive__:
            EmailAddress.__exclusive_backrefs__.add(backref_name)
        return db.relationship(EmailAddress, backref=backref_name)

    @declared_attr
    def email(cls):
        if cls.__email_for__:

            def email_get(self):
                if self.email_address:
                    return self.email_address.email

            def email_set(self, value):
                self.email_address = EmailAddress.add_for(
                    getattr(self, cls.__email_for__), value
                )

            return property(fget=email_get, fset=email_set)
        else:
            return association_proxy(
                'email_address', 'email', creator=lambda email: EmailAddress.add(email)
            )


auto_init_default(EmailAddress._delivery_state)
auto_init_default(EmailAddress.delivery_state_at)
auto_init_default(EmailAddress._is_blocked)


@event.listens_for(EmailAddress.email, 'set')
def _validate_email(target, value, old_value, initiator):
    # First: check if value is acceptable and email attribute can be set
    if not value and value is not None:
        # Only `None` is an acceptable falsy value
        raise ValueError("An email address is required")
    elif old_value == value:
        # Old value is new value. Do nothing. Return without validating
        return
    elif old_value is NO_VALUE and inspect(target).has_identity is False:
        # Old value is unknown and target is a transient object. Continue
        pass
    elif value is None:
        # Caller is trying to unset email. Allow this
        pass
    elif old_value is None:
        # Caller is trying to restore email. Allow but validate match for existing hash
        pass
    elif (
        isinstance(old_value, str)
        and isinstance(value, str)
        and old_value.lower() == value.lower()
    ):
        # Allow casing change in the email address (will be tested against hashed value)
        pass
    else:
        # Under any other condition, email is immutable
        raise ValueError("Email address cannot be changed")

    # Second: If we have a value, does it look like an email address?
    # This does not check if it's a reachable mailbox; merely if it has valid syntax
    if value and not is_email(value, check_dns=False, diagnose=False):
        raise ValueError("Value is not an email address")

    # All clear? Now update the hash as well
    if value is not None:
        hashed = email_blake2b160_hash(value.lower())
        if hashed != target.blake2b160:
            raise ValueError("Email address does not match existing blake2b160 hash")
    # We don't have to set target.email because SQLAlchemy will do that for us


# --- Tail imports ---------------------------------------------------------------------
from .user import User  # isort:skip
