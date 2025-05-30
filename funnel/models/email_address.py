"""Email address model, storing an email db distinctly from its uses."""

from __future__ import annotations

import hashlib
import unicodedata
import warnings
from collections.abc import MutableMapping
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, cast, overload

import base58
import idna
from mxsniff import mxsniff
from pyisemail import is_email
from pyisemail.diagnosis import BaseDiagnosis
from sqlalchemy import event, inspect
from sqlalchemy.orm import NO_VALUE, Mapper
from werkzeug.utils import cached_property

from coaster.sqlalchemy import (
    ModelWarning,
    StateManager,
    auto_init_default,
    immutable,
    with_roles,
)
from coaster.utils import LabeledEnum, require_one_of

from ..signals import emailaddress_refcount_dropping
from .base import (
    BaseMixin,
    Mapped,
    Model,
    Query,
    db,
    declarative_mixin,
    declared_attr,
    hybrid_property,
    relationship,
    sa,
    sa_orm,
)

__all__ = [
    'EMAIL_DELIVERY_STATE',
    'EmailAddress',
    'EmailAddressBlockedError',
    'EmailAddressError',
    'EmailAddressInUseError',
    'EmailAddressMixin',
    'OptionalEmailAddressMixin',
]


class EMAIL_DELIVERY_STATE(LabeledEnum):  # noqa: N801
    """
    Email delivery states. Use ``dict(EMAIL_DELIVERY_STATE)`` to get contents.

    The 'active' state here is used to distinguish from an abandoned mailbox that
    continues to receive messages, or one that drops them without reporting a bounce.
    For example, email delivery to the spam folder will appear sent but not active.
    The 'active' state is not a record of the activity of a recipient, as that requires
    tracking per email message sent and not per email address.

    The fail states require supporting infrastructure to record bounce reports from
    the email server. Active state requires incoming link handlers to report activity.
    """

    UNKNOWN = (1, 'unknown')  # Never mailed
    SENT = (2, 'sent')  # Mail sent, nothing further known
    # ACTIVE state (3, 'active') has been removed
    SOFT_FAIL = (4, 'soft_fail')  # Soft fail reported
    HARD_FAIL = (5, 'hard_fail')  # Hard fail reported


def canonical_email_representation(email: str) -> list[str]:
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
    if '@' not in email:
        raise ValueError("Not an email address")
    mailbox, domain = email.split('@', 1)
    mailbox = unicodedata.normalize('NFC', mailbox).lower()
    if '+' in mailbox:
        mailbox = mailbox[: mailbox.find('+')]
    domain = idna.encode(domain, uts46=True).decode()

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


def email_normalized(email: str) -> str:
    """
    Return a normalized representation of the email address, for unique hashing.

    Casts the mailbox portion into lowercase and encodes IDN domains into punycode. The
    resulting address remains valid for sending email, but the original should be used
    as the mailbox portion is technically case-sensitive, even if unlikely in practice.
    """
    mailbox, domain = email.split('@', 1)

    # RFC 6532 section 3.1 says Unicode NFC normalization should be used. We also
    # convert to lowercase on the assumption that two different casings on the same
    # domain are more likely a typing accident than intended use.
    mailbox = unicodedata.normalize('NFC', mailbox).lower()
    domain = idna.encode(domain, uts46=True).decode()
    return f'{mailbox}@{domain}'


def email_blake2b160_hash(email: str) -> bytes:
    """BLAKE2b hash of the given email address using digest size 20 (160 bits)."""
    return hashlib.blake2b(
        email_normalized(email).encode('utf-8'), digest_size=20
    ).digest()


class EmailAddressError(ValueError):
    """Base class for EmailAddress exceptions."""


class EmailAddressBlockedError(EmailAddressError):
    """Email address is blocked from use."""


class EmailAddressInUseError(EmailAddressError):
    """Email address is in use by another owner."""


class EmailAddress(BaseMixin[int, 'Account'], Model):
    """
    Represents an email address as a standalone entity, with associated metadata.

    Prior to this model, email addresses were regarded as properties of other models.
    Specifically: Proposal.email, Participant.email, Account.emails and
    Account.emailclaims, the latter two lists populated using the AccountEmail and
    AccountEmailClaim join models. This subordination made it difficult to track
    ownership of an email address or its reachability (active, bouncing, etc). Having
    EmailAddress as a standalone model (with incoming foreign keys) provides some
    sanity:

    1. Email addresses are stored with a hash, and always looked up using the hash. This
       allows the address to be forgotten while preserving the record for metadata.
    2. A forgotten address's record can be restored given the correct email address.
    3. Addresses can be automatically forgotten when they are no longer referenced. This
       ability is implemented using the :attr:`emailaddress_refcount_dropping` signal
       and supporting code in ``views/helpers.py`` and ``jobs/jobs.py``.
    4. If there is abuse, an email address can be comprehensively blocked using its
       canonical representation, which prevents the address from being used even via
       its ``+sub-address`` variations.
    5. Via :class:`EmailAddressMixin`, the AccountEmail model can establish ownership of
       an email address on behalf of a user, placing an automatic block on its use by
       other users. This mechanism is not limited to users. A future OrgEmail link can
       establish ownership on behalf of an organization.
    6. Upcoming: column-level encryption of the email column, securing SQL dumps.

    New email addresses must be added using the :meth:`add` or :meth:`add_for`
    class methods, depending on whether the email address is linked to an owner or not.
    """

    __tablename__ = 'email_address'

    #: Backrefs to this model from other models, populated by :class:`EmailAddressMixin`
    #: Contains the name of the relationship in the :class:`EmailAddress` model
    __backrefs__: ClassVar[set[str]] = set()
    #: These backrefs claim exclusive use of the email address for their linked owner.
    #: See :class:`OptionalEmailAddressMixin` for implementation detail
    __exclusive_backrefs__: ClassVar[set[str]] = set()

    #: The email address, centrepiece of this model. Case preserving.
    #: Validated by the :func:`_validate_email` event handler
    email: Mapped[str | None] = sa_orm.mapped_column()
    #: The domain of the email, stored for quick lookup of related addresses
    #: Read-only, accessible via the :property:`domain` property
    _domain: Mapped[str | None] = sa_orm.mapped_column('domain', index=True)

    # email_normalized is defined below

    #: BLAKE2b 160-bit hash of :property:`email_normalized`. Kept permanently even if
    #: email is removed. SQLAlchemy type LargeBinary maps to PostgreSQL BYTEA. Despite
    #: the name, we're only storing 20 bytes
    blake2b160: Mapped[bytes] = immutable(
        sa_orm.mapped_column(
            sa.LargeBinary,
            sa.CheckConstraint(
                'LENGTH(blake2b160) = 20',
                name='email_address_blake2b160_check',
            ),
            nullable=False,
            unique=True,
        )
    )

    #: BLAKE2b 160-bit hash of :property:`email_canonical`. Kept permanently for blocked
    #: email detection. Indexed but does not use a unique constraint because a+b@tld and
    #: a+c@tld are both a@tld canonically but can exist in records separately.
    blake2b160_canonical: Mapped[bytes] = immutable(
        sa_orm.mapped_column(sa.LargeBinary, nullable=False, index=True)
    )

    #: Does this email address work? Records last known delivery state
    _delivery_state: Mapped[int] = sa_orm.mapped_column(
        'delivery_state',
        sa.SmallInteger,
        StateManager.check_constraint(
            'delivery_state',
            EMAIL_DELIVERY_STATE,
            sa.SmallInteger,
            name='email_address_delivery_state_check',
        ),
        nullable=False,
        default=EMAIL_DELIVERY_STATE.UNKNOWN,
    )
    delivery_state = StateManager['EmailAddress'](
        '_delivery_state',
        EMAIL_DELIVERY_STATE,
        doc="Last known delivery state of this email address",
    )
    #: Timestamp of last known delivery state
    delivery_state_at: Mapped[datetime] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        insert_default=sa.func.utcnow(),
        default=None,
    )
    #: Timestamp of last known recipient activity resulting from sent mail
    active_at: Mapped[datetime | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )

    #: Is this email address blocked from being used? If so, :attr:`email` should be
    #: null. Blocks apply to the canonical address (without the +sub-address variation),
    #: so a test for whether an address is blocked should use blake2b160_canonical to
    #: load the record. Other records with the same canonical hash _may_ exist without
    #: setting the flag due to a lack of database-side enforcement
    _is_blocked: Mapped[bool] = sa_orm.mapped_column('is_blocked', default=False)

    __table_args__ = (
        # `domain` must be lowercase always. Note that Python `.lower()` is not
        # guaranteed to produce identical output to SQL `lower()` with non-ASCII
        # characters. It is only safe to use here because domain names are always ASCII
        sa.CheckConstraint(
            _domain == sa.func.lower(_domain), 'email_address_domain_check'
        ),
        # If `is_blocked` is True, `email` and `domain` must be None
        sa.CheckConstraint(
            sa.or_(
                _is_blocked.is_not(True),
                sa.and_(_is_blocked.is_(True), email.is_(None), _domain.is_(None)),
            ),
            'email_address_email_is_blocked_check',
        ),
        # `email` and `domain` must be None, or `email.endswith(domain)` must be True.
        # However, the endswith constraint is relaxed with IDN domains, as there is no
        # easy way to do an IDN match in Postgres without an extension.
        # `_` and `%` must be escaped as they are wildcards to the LIKE/ILIKE operator
        sa.CheckConstraint(
            sa.or_(
                # email and domain must both be non-null, or
                sa.and_(email.is_(None), _domain.is_(None)),
                # domain must be an IDN, or
                email.op('SIMILAR TO')('(xn--|%.xn--)%'),
                # domain is ASCII (typical case) and must be the suffix of email
                email.ilike(
                    '%'
                    + sa.func.replace(sa.func.replace(_domain, '_', r'\_'), '%', r'\%')
                ),
            ),
            'email_address_email_domain_check',
        ),
    )

    if TYPE_CHECKING:
        used_in_account_email: Mapped[list[AccountEmail]] = relationship()
        used_in_account_email_claim: Mapped[list[AccountEmailClaim]] = relationship()
        used_in_ticket_participant: Mapped[list[TicketParticipant]] = relationship()

    @hybrid_property
    def is_blocked(self) -> bool:
        """
        Read-only flag indicating this email address is blocked from use.

        To set this flag, call :classmethod:`mark_blocked` using the email address. The
        flag will be simultaneously set on all matching instances.
        """
        with db.session.no_autoflush:
            return self._is_blocked

    @hybrid_property
    def domain(self) -> str | None:
        """Domain of the email, stored for quick lookup of related addresses."""
        return self._domain

    # This should not use `cached_property` as email is partially mutable
    @property
    def email_normalized(self) -> str | None:
        """Return normalized representation of the email address, for hashing."""
        return email_normalized(self.email) if self.email else None

    # This should not use `cached_property` as email is partially mutable
    @property
    def email_canonical(self) -> str | None:
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

    # Compatibility name for notifications framework
    transport_hash = email_hash

    @with_roles(call={'all'})
    def md5(self) -> str | None:
        """MD5 hash of :property:`email_normalized`, for legacy use only."""
        return (
            hashlib.md5(
                self.email_normalized.encode('utf-8'), usedforsecurity=False
            ).hexdigest()
            if self.email_normalized
            else None
        )

    def __str__(self) -> str:
        """Cast email address into a string."""
        return self.email or ''

    def __format__(self, format_spec: str) -> str:
        """Format the email address."""
        if not format_spec:
            return self.__str__()
        return format(self.__str__(), format_spec)

    def __repr__(self) -> str:
        """Debugging representation of the email address."""
        return f'EmailAddress({self.email!r})'

    def __init__(self, email: str) -> None:
        super().__init__()
        if not isinstance(email, str):
            raise ValueError("A string email address is required")
        # Set the hash first so the email column validator passes. Both hash columns
        # are immutable once set, so there are no content validators for them.
        try:
            self.blake2b160 = email_blake2b160_hash(email)
        except idna.InvalidCodepoint as exc:
            raise ValueError("Value is not an email address") from exc
        self.email = email
        # email_canonical is set by `email`'s validator
        assert self.email_canonical is not None  # noqa: S101
        self.blake2b160_canonical = email_blake2b160_hash(self.email_canonical)

    def is_exclusive(self) -> bool:
        """Return True if this EmailAddress is in an exclusive relationship."""
        return any(
            related_obj
            for backref_name in self.__exclusive_backrefs__
            for related_obj in getattr(self, backref_name)
        )

    def is_available_for(self, owner: Account | None) -> bool:
        """Return True if this EmailAddress is available for the proposed owner."""
        for backref_name in self.__exclusive_backrefs__:
            for related_obj in getattr(self, backref_name):
                curr_owner = getattr(related_obj, related_obj.__email_for__)
                if curr_owner is not None and curr_owner != owner:
                    return False
        return True

    def is_public_provider(self, cache: MutableMapping | None = None) -> bool:
        """
        Check if this email address is from a known public provider (Gmail, etc).

        This performs a DNS lookup for unknown domains. Providing a cache is highly
        recommended. The cache object must implement the
        :class:`~collections.abc.MutableMapping` API.
        """
        if not self.domain:
            raise ValueError("Can't lookup a removed email address.")
        lookup = mxsniff(self.domain, cache=cache)
        return lookup['public']

    @delivery_state.transition(None, delivery_state.SENT)
    def mark_sent(self) -> None:
        """Record fact of an email message being sent to this address."""
        self.delivery_state_at = sa.func.utcnow()

    def mark_active(self) -> None:
        """Record timestamp of recipient activity."""
        self.active_at = sa.func.utcnow()

    @delivery_state.transition(None, delivery_state.SOFT_FAIL)
    def mark_soft_fail(self) -> None:
        """Record fact of a soft fail to this email address."""
        self.delivery_state_at = sa.func.utcnow()

    @delivery_state.transition(None, delivery_state.HARD_FAIL)
    def mark_hard_fail(self) -> None:
        """Record fact of a hard fail to this email address."""
        self.delivery_state_at = sa.func.utcnow()

    def refcount(self) -> int:
        """Count of references to this :class:`EmailAddress` instance."""
        # obj.email_address_reference_is_active is a bool, but int(bool) is 0 or 1
        return sum(
            sum(
                obj.email_address_reference_is_active
                for obj in getattr(self, backref_name)
            )
            for backref_name in self.__backrefs__
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
            obj.email = None
            obj._is_blocked = True  # pylint: disable=protected-access

    @overload
    @classmethod
    def get_filter(cls, *, email: str) -> sa.ColumnElement[bool] | None: ...

    @overload
    @classmethod
    def get_filter(cls, *, blake2b160: bytes) -> sa.ColumnElement[bool]: ...

    @overload
    @classmethod
    def get_filter(cls, *, email_hash: str) -> sa.ColumnElement[bool]: ...

    @overload
    @classmethod
    def get_filter(
        cls,
        *,
        email: str | None,
        blake2b160: bytes | None,
        email_hash: str | None,
    ) -> sa.ColumnElement[bool] | None: ...

    @classmethod
    def get_filter(
        cls,
        *,
        email: str | None = None,
        blake2b160: bytes | None = None,
        email_hash: str | None = None,
    ) -> sa.ColumnElement[bool] | None:
        """
        Get an filter condition for retrieving an :class:`EmailAddress`.

        Accepts an email address or a blake2b160 hash in either bytes or base58 form.
        Internally converts all lookups to a bytes-based hash lookup. Returns an
        expression suitable for use as a query filter.
        """
        require_one_of(email=email, blake2b160=blake2b160, email_hash=email_hash)
        if email:
            if not cls.is_valid_email_address(email):
                return None
            blake2b160 = email_blake2b160_hash(email)
        elif email_hash:
            blake2b160 = base58.b58decode(email_hash)

        return cls.blake2b160 == blake2b160

    @overload
    @classmethod
    def get(
        cls,
        email: str,
    ) -> Self | None: ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        blake2b160: bytes,
    ) -> Self | None: ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        email_hash: str,
    ) -> Self | None: ...

    @classmethod
    def get(
        cls,
        email: str | None = None,
        *,
        blake2b160: bytes | None = None,
        email_hash: str | None = None,
    ) -> Self | None:
        """
        Get an :class:`EmailAddress` instance by email address or its hash.

        Internally converts an email-based lookup into a hash-based lookup.
        """
        email_filter = cls.get_filter(
            email=email, blake2b160=blake2b160, email_hash=email_hash
        )
        if email_filter is None:
            return None
        return cls.query.filter(email_filter).one_or_none()

    @classmethod
    def get_canonical(cls, email: str, is_blocked: bool | None = None) -> Query[Self]:
        """
        Get :class:`EmailAddress` instances matching the canonical representation.

        Optionally filtered by the :attr:`is_blocked` flag.
        """
        hashes = [
            email_blake2b160_hash(result)
            for result in canonical_email_representation(email)
        ]
        query = cls.query.filter(cls.blake2b160_canonical.in_(hashes))
        if is_blocked is not None:
            query = query.filter_by(_is_blocked=is_blocked)
        return query

    @classmethod
    def _get_existing(cls, email: str) -> Self | None:
        """
        Get an existing :class:`EmailAddress` instance.

        Internal method used by :meth:`add`, :meth:`add_for` and :meth:`validate_for`.
        """
        if not cls.is_valid_email_address(email):
            return None
        if cls.get_canonical(email, is_blocked=True).notempty():
            raise EmailAddressBlockedError("Email address is blocked")
        return cls.get(email)

    @classmethod
    def add(cls, email: str) -> Self:
        """
        Create a new :class:`EmailAddress` after validation.

        Raises an exception if the address is blocked from use, or the email address
        is syntactically invalid.

        :raises ValueError: If email address syntax is invalid
        :raises EmailAddressBlockedError: If email address is blocked
        """
        existing = cls._get_existing(email)
        if existing is not None:
            # Restore the email column if it's not present. Do not modify it otherwise
            if not existing.email:
                existing.email = email
            return existing
        new_email = cls(email)
        db.session.add(new_email)
        return new_email

    @classmethod
    def add_for(cls, owner: Account | None, email: str) -> Self:
        """
        Create a new :class:`EmailAddress` after validation.

        Unlike :meth:`add`, this one requires the email address to not be in an
        exclusive relationship with another owner.
        """
        existing = cls._get_existing(email)
        if existing is not None:
            if not existing.is_available_for(owner):
                raise EmailAddressInUseError("This email address is in use")
            # No exclusive lock found? Let it be used then
            existing.email = email
            return existing
        new_email = cls(email)
        db.session.add(new_email)
        return new_email

    @classmethod
    def validate_for(
        cls,
        owner: Account | None,
        email: str,
        check_dns: bool = False,
        new: bool = False,
    ) -> (
        Literal[
            'taken',
            'nomx',
            'not_new',
            'soft_fail',
            'hard_fail',
            'invalid',
            'nullmx',
            'blocked',
        ]
        | None
    ):
        """
        Validate whether the email address is available to the proposed owner.

        Returns None if available without issues, or a string value indicating the
        concern:

        1. 'taken': Email address has another owner
        2. 'nomx': Email address is available, but has no MX records
        3. 'not_new': Email address is already attached to owner (if `new` is True)
        4. 'soft_fail': Known to be soft bouncing, requiring a warning message
        5. 'hard_fail': Known to be hard bouncing, usually a validation failure
        6. 'invalid': Available, but failed syntax validation
        7. 'nullmx': Available, but host explicitly says they will not accept email
        8. 'blocked': Email address is blocked from use

        :param owner: Proposed owner of this email address (may be None)
        :param email: Email address to validate
        :param check_dns: Check for MX records for a new email address
        :param new: Fail validation if email address is already in use by owner
        """
        try:
            existing = cls._get_existing(email)
        except EmailAddressBlockedError:
            return 'blocked'
        if existing is None:
            diagnosis = cls.is_valid_email_address(
                email, check_dns=check_dns, diagnose=True
            )
            if diagnosis is True:
                # There is no existing record, and the email address has no problems
                return None
            # get_canonical won't return False when diagnose=True. Tell mypy:
            if cast(BaseDiagnosis, diagnosis).diagnosis_type == 'NO_MX_RECORD':
                return 'nomx'
            if cast(BaseDiagnosis, diagnosis).diagnosis_type == 'NULL_MX_RECORD':
                return 'nullmx'
            return 'invalid'
        # There's an existing? Is it available for this owner?
        if not existing.is_available_for(owner):
            # Already taken by another owner
            return 'taken'

        # There is an existing but it's available for this owner. Any other concerns?
        if new and existing.is_exclusive():
            # Caller is asking to confirm this is not already belonging to this owner:
            # It's in an exclusive relationship, and we're already determined it's
            # available to this owner, so it must be exclusive to them
            return 'not_new'
        if existing.delivery_state.SOFT_FAIL:
            return 'soft_fail'
        if existing.delivery_state.HARD_FAIL:
            return 'hard_fail'
        return None

    @staticmethod
    def is_valid_email_address(
        email: str, check_dns: bool = False, diagnose: bool = False
    ) -> bool | BaseDiagnosis:
        """
        Return True if given email address is syntactically valid.

        This implementation will refuse to accept unusual elements such as quoted
        strings, as they are unlikely to appear in real-world use.

        :param bool check_dns: Optionally, check for existence of MX records
        :param bool diagnose: In case of errors only, return the diagnosis
        """
        if email:
            result = is_email(email, check_dns=check_dns, diagnose=True)
            if result.diagnosis_type in ('VALID', 'NO_NAMESERVERS', 'DNS_TIMEDOUT'):
                return True
            return result if diagnose else False
        return False


@declarative_mixin
class OptionalEmailAddressMixin:
    """
    Mixin class for models that refer to :class:`EmailAddress`.

    Subclasses should set configuration using the four ``__email_*__`` attributes and
    should optionally override :meth:`email_address_reference_is_active` if the model
    implements archived rows, such as in memberships.
    """

    # Provided by subclasses
    __tablename__: str

    #: This class has an optional dependency on EmailAddress
    __email_optional__: ClassVar[bool] = True
    #: This class has a unique constraint on the fkey to EmailAddress
    __email_unique__: ClassVar[bool] = False
    #: A relationship from this model is for the (single) owner at this attr
    __email_for__: ClassVar[str | None] = None
    #: If `__email_for__` is specified and this flag is True, the email address is
    #: considered exclusive to this owner and may not be used by any other owner
    __email_is_exclusive__: ClassVar[bool] = False

    @declared_attr
    @classmethod
    def email_address_id(cls) -> Mapped[int | None]:
        """Foreign key to email_address table."""
        return sa_orm.mapped_column(
            sa.Integer,
            sa.ForeignKey('email_address.id', ondelete='SET NULL'),
            default=None,
            nullable=cls.__email_optional__,
            unique=cls.__email_unique__,
            index=not cls.__email_unique__,
        )

    @declared_attr
    @classmethod
    def email_address(cls) -> Mapped[EmailAddress | None]:
        """Instance of :class:`EmailAddress` as a relationship."""
        backref_name = 'used_in_' + cls.__tablename__
        EmailAddress.__backrefs__.add(backref_name)
        if cls.__email_for__ and cls.__email_is_exclusive__:
            EmailAddress.__exclusive_backrefs__.add(backref_name)
        with warnings.catch_warnings(action='ignore', category=ModelWarning):
            return relationship(EmailAddress, backref=backref_name)

    @property
    def email(self) -> str | None:
        """
        Shorthand for ``self.email_address.email``.

        Setting a value does the equivalent of one of these, depending on whether
        the object requires the email address to be available to its owner::

            self.email_address = EmailAddress.add(email)
            self.email_address = EmailAddress.add_for(owner, email)

        Where the owner is found from the attribute named in `cls.__email_for__`.
        """
        if self.email_address:
            return self.email_address.email
        return None

    @email.setter
    def email(self, __value: str | None, /) -> None:
        """Set an email address."""
        if self.__email_for__:
            if __value is not None:
                self.email_address = EmailAddress.add_for(
                    getattr(self, self.__email_for__), __value
                )
            else:
                self.email_address = None

        elif __value is not None:
            self.email_address = EmailAddress.add(__value)
        else:
            self.email_address = None

    @property
    def email_address_reference_is_active(self) -> bool:
        """
        Assert that the reference to an email address is valid, requiring it to be kept.

        Subclasses should override to return `False` if they hold inactive references
        and approve of the email address being forgotten.
        """
        return True

    @property
    def transport_hash(self) -> str | None:
        """Email hash using the compatibility name for notifications framework."""
        return (
            self.email_address.email_hash
            if self.email_address  # pylint: disable=using-constant-test
            else None
        )


@declarative_mixin
class EmailAddressMixin(OptionalEmailAddressMixin):
    """Non-optional version of :class:`OptionalEmailAddressMixin`."""

    __email_optional__: ClassVar[bool] = False

    if TYPE_CHECKING:

        @declared_attr
        @classmethod
        def email_address_id(cls) -> Mapped[int]:  # type: ignore[override]
            ...

        @declared_attr
        @classmethod
        def email_address(cls) -> Mapped[EmailAddress]:  # type: ignore[override]
            ...

        @property  # type: ignore[override]
        def email(self) -> str: ...

        @email.setter
        def email(self, __value: str, /) -> None: ...

        @property
        def transport_hash(self) -> str: ...


auto_init_default(EmailAddress._delivery_state)  # pylint: disable=protected-access
auto_init_default(EmailAddress.delivery_state_at)
auto_init_default(EmailAddress._is_blocked)  # pylint: disable=protected-access


@event.listens_for(EmailAddress.email, 'set')
def _validate_email(
    target: EmailAddress, value: Any, old_value: Any, _initiator: Any
) -> None:
    # First: check if value is acceptable and email attribute can be set
    if not value and value is not None:
        # Only `None` is an acceptable falsy value
        raise ValueError("An email address is required")
    if old_value == value:
        # Old value is new value. Do nothing. Return without validating
        return
    if old_value is NO_VALUE and inspect(target).has_identity is False:
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
    if value is not None and not (
        isinstance(value, str) and EmailAddress.is_valid_email_address(value)
    ):
        raise ValueError("Value is not an email address")

    # All clear? Now check against the hash
    if value is not None:
        hashed = email_blake2b160_hash(value)
        if hashed != target.blake2b160:
            raise ValueError("Email address does not match existing blake2b160 hash")
        target._domain = idna.encode(  # pylint: disable=protected-access
            value.split('@', 1)[1], uts46=True
        ).decode()
    else:
        target._domain = None  # pylint: disable=protected-access
    # We don't have to set target.email because SQLAlchemy will do that for us.


def _send_refcount_event_remove(
    target: EmailAddress, _value: Any, _initiator: Any
) -> None:
    emailaddress_refcount_dropping.send(target)


def _send_refcount_event_before_delete(
    _mapper: Any, _connection: Any, target: OptionalEmailAddressMixin
) -> None:
    if target.email_address:
        emailaddress_refcount_dropping.send(target.email_address)


@event.listens_for(Mapper, 'after_configured')
def _setup_refcount_events() -> None:
    for backref_name in EmailAddress.__backrefs__:
        attr = getattr(EmailAddress, backref_name)
        event.listen(attr, 'remove', _send_refcount_event_remove)


def _email_address_mixin_set_validator(
    target: OptionalEmailAddressMixin,
    value: EmailAddress | None,
    old_value: EmailAddress | None,
    _initiator: Any,
) -> None:
    if value != old_value and target.__email_for__ and value is not None:
        if value.is_blocked:
            raise EmailAddressBlockedError("This email address has been blocked")
        if not value.is_available_for(getattr(target, target.__email_for__)):
            raise EmailAddressInUseError("This email address it not available")


@event.listens_for(OptionalEmailAddressMixin, 'mapper_configured', propagate=True)
def _email_address_mixin_configure_events(
    _mapper: Any, cls: type[OptionalEmailAddressMixin]
) -> None:
    event.listen(cls.email_address, 'set', _email_address_mixin_set_validator)
    event.listen(cls, 'before_delete', _send_refcount_event_before_delete)


if TYPE_CHECKING:
    from .account import Account, AccountEmail, AccountEmailClaim
    from .sync_ticket import TicketParticipant
