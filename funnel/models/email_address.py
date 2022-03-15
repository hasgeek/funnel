from __future__ import annotations

from typing import List, Optional, Set, Union, cast, overload
import hashlib
import unicodedata

from sqlalchemy import event, inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import mapper
from sqlalchemy.orm.attributes import NO_VALUE
from sqlalchemy.sql.expression import BinaryExpression

from werkzeug.utils import cached_property

from pyisemail import is_email
from pyisemail.diagnosis import BaseDiagnosis
import base58
import idna

from coaster.sqlalchemy import (
    Query,
    StateManager,
    auto_init_default,
    immutable,
    with_roles,
)
from coaster.utils import LabeledEnum, require_one_of

from ..signals import emailaddress_refcount_dropping
from . import BaseMixin, db, hybrid_property

__all__ = [
    'EMAIL_DELIVERY_STATE',
    'EmailAddressError',
    'EmailAddressBlockedError',
    'EmailAddressInUseError',
    'EmailAddress',
    'EmailAddressMixin',
]


class EMAIL_DELIVERY_STATE(LabeledEnum):
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

    UNKNOWN = (0, 'unknown')  # Never mailed
    SENT = (1, 'sent')  # Mail sent, nothing further known
    # ACTIVE state (2, 'active') has been removed
    SOFT_FAIL = (3, 'soft_fail')  # Soft fail reported
    HARD_FAIL = (4, 'hard_fail')  # Hard fail reported


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


class EmailAddress(BaseMixin, db.Model):
    """
    Represents an email address as a standalone entity, with associated metadata.

    Prior to this model, email addresses were regarded as properties of other models.
    Specifically: Proposal.email, Participant.email, User.emails and User.emailclaims,
    the latter two lists populated using the UserEmail and UserEmailClaim join models.
    This subordination made it difficult to track ownership of an email address or its
    reachability (active, bouncing, etc). Having EmailAddress as a standalone model
    (with incoming foreign keys) provides some sanity:

    1. Email addresses are stored with a hash, and always looked up using the hash. This
       allows the address to be forgotten while preserving the record for metadata.
    2. A forgotten address's record can be restored given the correct email address.
    3. Addresses can be automatically forgotten when they are no longer referenced. This
       ability is implemented using the :attr:`emailaddress_refcount_dropping` signal
       and supporting code in ``views/helpers.py`` and ``jobs/jobs.py``.
    4. If there is abuse, an email address can be comprehensively blocked using its
       canonical representation, which prevents the address from being used even via
       its ``+sub-address`` variations.
    5. Via :class:`EmailAddressMixin`, the UserEmail model can establish ownership of
       an email address on behalf of a user, placing an automatic block on its use by
       other users. This mechanism is not limited to users. A future OrgEmail link can
       establish ownership on behalf of an organization.
    6. Upcoming: column-level encryption of the email column, securing SQL dumps.

    New email addresses must be added using the :meth:`add` or :meth:`add_for`
    classmethods, depending on whether the email address is linked to an owner or not.
    """

    __tablename__ = 'email_address'

    #: Backrefs to this model from other models, populated by :class:`EmailAddressMixin`
    #: Contains the name of the relationship in the :class:`EmailAddress` model
    __backrefs__: Set[str] = set()
    #: These backrefs claim exclusive use of the email address for their linked owner.
    #: See :class:`EmailAddressMixin` for implementation detail
    __exclusive_backrefs__: Set[str] = set()

    #: The email address, centrepiece of this model. Case preserving.
    #: Validated by the :func:`_validate_email` event handler
    email = db.Column(db.Unicode, nullable=True)
    #: The domain of the email, stored for quick lookup of related addresses
    #: Read-only, accessible via the :property:`domain` property
    _domain = db.Column('domain', db.Unicode, nullable=True, index=True)

    # email_normalized is defined below

    #: BLAKE2b 160-bit hash of :property:`email_normalized`. Kept permanently even if
    #: email is removed. SQLAlchemy type LargeBinary maps to PostgreSQL BYTEA. Despite
    #: the name, we're only storing 20 bytes
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
        StateManager.check_constraint(
            'delivery_state',
            EMAIL_DELIVERY_STATE,
            name='email_address_delivery_state_check',
        ),
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
    #: Timestamp of last known recipient activity resulting from sent mail
    active_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    #: Is this email address blocked from being used? If so, :attr:`email` should be
    #: null. Blocks apply to the canonical address (without the +sub-address variation),
    #: so a test for whether an address is blocked should use blake2b160_canonical to
    #: load the record. Other records with the same canonical hash _may_ exist without
    #: setting the flag due to a lack of database-side enforcement
    _is_blocked = db.Column('is_blocked', db.Boolean, nullable=False, default=False)

    __table_args__ = (
        # `domain` must be lowercase always. Note that Python `.lower()` is not
        # guaranteed to produce identical output to SQL `lower()` with non-ASCII
        # characters. It is only safe to use here because domain names are always ASCII
        db.CheckConstraint(
            _domain == db.func.lower(_domain), 'email_address_domain_check'
        ),
        # If `is_blocked` is True, `email` and `domain` must be None
        db.CheckConstraint(
            db.or_(
                _is_blocked.isnot(True),
                db.and_(_is_blocked.is_(True), email.is_(None), _domain.is_(None)),
            ),
            'email_address_email_is_blocked_check',
        ),
        # `email` and `domain` must be None, or `email.endswith(domain)` must be True.
        # However, the endswith constraint is relaxed with IDN domains, as there is no
        # easy way to do an IDN match in Postgres without an extension.
        # `_` and `%` must be escaped as they are wildcards to the LIKE/ILIKE operator
        db.CheckConstraint(
            db.or_(
                # email and domain must both be non-null, or
                db.and_(email.is_(None), _domain.is_(None)),
                # domain must be an IDN, or
                email.op('SIMILAR TO')('(xn--|%.xn--)%'),
                # domain is ASCII (typical case) and must be the suffix of email
                email.ilike(
                    '%'
                    + db.func.replace(db.func.replace(_domain, '_', r'\_'), '%', r'\%')
                ),
            ),
            'email_address_email_domain_check',
        ),
    )

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
    def domain(self) -> Optional[str]:
        """Domain of the email, stored for quick lookup of related addresses."""
        return self._domain

    # This should not use `cached_property` as email is partially mutable
    @property
    def email_normalized(self) -> Optional[str]:
        """Return normalized representation of the email address, for hashing."""
        return email_normalized(self.email) if self.email else None

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

    # Compatibility name for notifications framework
    transport_hash = email_hash

    @with_roles(call={'all'})
    def md5(self) -> Optional[str]:
        """MD5 hash of :property:`email_normalized`, for legacy use only."""
        return (
            hashlib.md5(  # nosec    # skipcq: PTC-W1003
                self.email_normalized.encode('utf-8')
            ).hexdigest()
            if self.email_normalized
            else None
        )

    def __str__(self) -> str:
        """Cast email address into a string."""
        return self.email or ''

    def __repr__(self) -> str:
        """Debugging representation of the email address."""
        return f'EmailAddress({self.email!r})'

    def __init__(self, email: str) -> None:
        if not isinstance(email, str):
            raise ValueError("A string email address is required")
        # Set the hash first so the email column validator passes. Both hash columns
        # are immutable once set, so there are no content validators for them.
        self.blake2b160 = email_blake2b160_hash(email)
        self.email = email
        # email_canonical is set by `email`'s validator
        assert self.email_canonical is not None  # nosec
        self.blake2b160_canonical = email_blake2b160_hash(self.email_canonical)

    def is_exclusive(self) -> bool:
        """Return True if this EmailAddress is in an exclusive relationship."""
        return any(
            related_obj
            for backref_name in self.__exclusive_backrefs__
            for related_obj in getattr(self, backref_name)
        )

    def is_available_for(self, owner: object) -> bool:
        """Return True if this EmailAddress is available for the given owner."""
        for backref_name in self.__exclusive_backrefs__:
            for related_obj in getattr(self, backref_name):
                curr_owner = getattr(related_obj, related_obj.__email_for__)
                if curr_owner is not None and curr_owner != owner:
                    return False
        return True

    @delivery_state.transition(None, delivery_state.SENT)
    def mark_sent(self) -> None:
        """Record fact of an email message being sent to this address."""
        self.delivery_state_at = db.func.utcnow()

    def mark_active(self) -> None:
        """Record timestamp of recipient activity."""
        self.active_at = db.func.utcnow()

    @delivery_state.transition(None, delivery_state.SOFT_FAIL)
    def mark_soft_fail(self) -> None:
        """Record fact of a soft fail to this email address."""
        self.delivery_state_at = db.func.utcnow()

    @delivery_state.transition(None, delivery_state.HARD_FAIL)
    def mark_hard_fail(self) -> None:
        """Record fact of a hard fail to this email address."""
        self.delivery_state_at = db.func.utcnow()

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
            obj._is_blocked = True

    @overload
    @classmethod
    def get_filter(cls, *, email: str) -> Optional[BinaryExpression]:
        ...

    @overload
    @classmethod
    def get_filter(cls, *, blake2b160: bytes) -> BinaryExpression:
        ...

    @overload
    @classmethod
    def get_filter(cls, *, email_hash: str) -> BinaryExpression:
        ...

    @overload
    @classmethod
    def get_filter(
        cls,
        *,
        email: Optional[str],
        blake2b160: Optional[bytes],
        email_hash: Optional[str],
    ) -> Optional[BinaryExpression]:
        ...

    @classmethod
    def get_filter(
        cls,
        *,
        email: Optional[str] = None,
        blake2b160: Optional[bytes] = None,
        email_hash: Optional[str] = None,
    ) -> Optional[BinaryExpression]:
        """
        Get an filter condition for retriving an EmailAddress.

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
    ) -> Optional[EmailAddress]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        blake2b160: bytes,
    ) -> Optional[EmailAddress]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        email_hash: str,
    ) -> Optional[EmailAddress]:
        ...

    @classmethod
    def get(
        cls,
        email: Optional[str] = None,
        *,
        blake2b160: Optional[bytes] = None,
        email_hash: Optional[str] = None,
    ) -> Optional[EmailAddress]:
        """
        Get an :class:`EmailAddress` instance by email address or its hash.

        Internally converts an email-based lookup into a hash-based lookup.
        """
        return cls.query.filter(
            cls.get_filter(email=email, blake2b160=blake2b160, email_hash=email_hash)
        ).one_or_none()

    @classmethod
    def get_canonical(cls, email: str, is_blocked: Optional[bool] = None) -> Query:
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
    def _get_existing(cls, email: str) -> Optional[EmailAddress]:
        """
        Get an existing :class:`EmailAddress` instance.

        Internal method used by :meth:`add`, :meth:`add_for` and :meth:`validate_for`.
        """
        if not cls.is_valid_email_address(email):
            return None
        if cls.get_canonical(email, is_blocked=True).notempty():
            raise EmailAddressBlockedError("Email address is blocked")
        return EmailAddress.get(email)

    @classmethod
    def add(cls, email: str) -> EmailAddress:
        """
        Create a new :class:`EmailAddress` after validation.

        Raises an exception if the address is blocked from use, or the email address
        is syntactically invalid.
        """
        existing = cls._get_existing(email)
        if existing is not None:
            # Restore the email column if it's not present. Do not modify it otherwise
            if not existing.email:
                existing.email = email
            return existing
        new_email = EmailAddress(email)
        db.session.add(new_email)
        return new_email

    @classmethod
    def add_for(cls, owner: Optional[object], email: str) -> EmailAddress:
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
        new_email = EmailAddress(email)
        db.session.add(new_email)
        return new_email

    @classmethod
    def validate_for(
        cls,
        owner: Optional[object],
        email: str,
        check_dns: bool = False,
        new: bool = False,
    ) -> Union[bool, str]:
        """
        Validate whether the email address is available to the given owner.

        Returns False if the address is blocked or in use by another owner, True if
        available without issues, or a string value indicating the concern:

        1. 'nomx': Email address is available, but has no MX records
        2. 'not_new': Email address is already attached to owner (if `new` is True)
        3. 'soft_fail': Known to be soft bouncing, requiring a warning message
        4. 'hard_fail': Known to be hard bouncing, usually a validation failure
        5. 'invalid': Available, but failed syntax validation

        :param owner: Proposed owner of this email address (may be None)
        :param str email: Email address to validate
        :param bool check_dns: Check for MX records for a new email address
        :param bool new: Fail validation if email address is already in use
        """
        try:
            existing = cls._get_existing(email)
        except EmailAddressBlockedError:
            return False
        if existing is None:
            diagnosis = cls.is_valid_email_address(
                email, check_dns=check_dns, diagnose=True
            )
            if diagnosis is True:
                # No problems
                return True
            # get_canonical won't return False when diagnose=True. Tell mypy:
            if cast(BaseDiagnosis, diagnosis).diagnosis_type == 'NO_MX_RECORD':
                return 'nomx'
            return 'invalid'
        # There's an existing? Is it available for this owner?
        if not existing.is_available_for(owner):
            # Not available, so return False
            return False

        # Available. Any other concerns?
        if new:
            # Caller is asking to confirm this is not already belonging to this owner
            if existing.is_exclusive():
                # It's in an exclusive relationship, and we're already determined it's
                # available to this owner, so it must be exclusive to them
                return 'not_new'
        if existing.delivery_state.SOFT_FAIL:
            return 'soft_fail'
        elif existing.delivery_state.HARD_FAIL:
            return 'hard_fail'
        return True

    @staticmethod
    def is_valid_email_address(
        email: str, check_dns: bool = False, diagnose: bool = False
    ) -> Union[bool, BaseDiagnosis]:
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


class EmailAddressMixin:
    """
    Mixin class for models that refer to EmailAddress.

    Subclasses should set configuration using the four ``__email_*__`` attributes and
    should optionally override :meth:`email_address_reference_is_active` if the model
    implements archived rows, such as in memberships.
    """

    # Provided by subclasses
    __tablename__: str

    #: This class has an optional dependency on EmailAddress
    __email_optional__: bool = True
    #: This class has a unique constraint on the fkey to EmailAddress
    __email_unique__: bool = False
    #: A relationship from this model is for the (single) owner at this attr
    __email_for__: Optional[str] = None
    #: If `__email_for__` is specified and this flag is True, the email address is
    #: considered exclusive to this owner and may not be used by any other owner
    __email_is_exclusive__: bool = False

    email_address_id: int

    @declared_attr  # type: ignore[no-redef]
    def email_address_id(cls):
        return db.Column(
            None,
            db.ForeignKey('email_address.id', ondelete='SET NULL'),
            nullable=cls.__email_optional__,
            unique=cls.__email_unique__,
            index=not cls.__email_unique__,
        )

    email_address: Optional[EmailAddress]

    @declared_attr  # type: ignore[no-redef]
    def email_address(cls):
        backref_name = 'used_in_' + cls.__tablename__
        EmailAddress.__backrefs__.add(backref_name)
        if cls.__email_for__ and cls.__email_is_exclusive__:
            EmailAddress.__exclusive_backrefs__.add(backref_name)
        return db.relationship(EmailAddress, backref=backref_name)

    email: Optional[str]

    @declared_attr  # type: ignore[no-redef]
    def email(cls):
        def email_get(self):
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

        if cls.__email_for__:

            def email_set(self, value):
                if value is not None:
                    self.email_address = EmailAddress.add_for(
                        getattr(self, cls.__email_for__), value
                    )
                else:
                    self.email_address = None

        else:

            def email_set(self, value):
                if value is not None:
                    self.email_address = EmailAddress.add(value)
                else:
                    self.email_address = None

        return property(fget=email_get, fset=email_set)

    @property
    def email_address_reference_is_active(self) -> bool:
        """
        Assert that the reference to an email address is valid, requiring it to be kept.

        Subclasses should override to return `False` if they hold inactive references
        and approve of the email address being forgotten.
        """
        return True

    @property
    def transport_hash(self) -> Optional[str]:
        """Email hash using the compatibility name for notifications framework."""
        return self.email_address.email_hash if self.email_address else None


auto_init_default(EmailAddress._delivery_state)
auto_init_default(EmailAddress.delivery_state_at)
auto_init_default(EmailAddress._is_blocked)


@event.listens_for(EmailAddress.email, 'set')
def _validate_email(target, value: object, old_value: object, initiator):
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
    if value is not None and not (
        isinstance(value, str) and EmailAddress.is_valid_email_address(value)
    ):
        raise ValueError("Value is not an email address")

    # All clear? Now check against the hash
    if value is not None:
        hashed = email_blake2b160_hash(value)
        if hashed != target.blake2b160:
            raise ValueError("Email address does not match existing blake2b160 hash")
        target._domain = idna.encode(value.split('@', 1)[1], uts46=True).decode()
    else:
        target._domain = None
    # We don't have to set target.email because SQLAlchemy will do that for us.


def _send_refcount_event_remove(target, value, initiator):
    emailaddress_refcount_dropping.send(target)


def _send_refcount_event_before_delete(mapper_, connection, target):
    if target.email_address:
        emailaddress_refcount_dropping.send(target.email_address)


@event.listens_for(mapper, 'after_configured')
def _setup_refcount_events() -> None:
    for backref_name in EmailAddress.__backrefs__:
        attr = getattr(EmailAddress, backref_name)
        event.listen(attr, 'remove', _send_refcount_event_remove)


def _email_address_mixin_set_validator(
    target, value: Optional[EmailAddress], old_value, initiator
) -> None:
    if value != old_value and target.__email_for__:
        if value is not None:
            if value.is_blocked:
                raise EmailAddressBlockedError("This email address has been blocked")
            if not value.is_available_for(getattr(target, target.__email_for__)):
                raise EmailAddressInUseError("This email address it not available")


@event.listens_for(EmailAddressMixin, 'mapper_configured', propagate=True)
def _email_address_mixin_configure_events(mapper_, cls: db.Model):
    event.listen(cls.email_address, 'set', _email_address_mixin_set_validator)
    event.listen(cls, 'before_delete', _send_refcount_event_before_delete)
