"""Phone number model, storing a number distinct from its uses."""

from __future__ import annotations

from typing import Any, Optional, Set, Union, overload
import hashlib

from sqlalchemy import event, inspect
from sqlalchemy.orm import mapper
from sqlalchemy.orm.attributes import NO_VALUE
from sqlalchemy.sql.expression import ColumnElement

from werkzeug.utils import cached_property

from typing_extensions import Literal
import base58
import phonenumbers

from baseframe import _
from coaster.sqlalchemy import immutable, with_roles
from coaster.utils import require_one_of

from ..signals import phonenumber_refcount_dropping
from . import (
    BaseMixin,
    Mapped,
    db,
    declarative_mixin,
    declared_attr,
    hybrid_property,
    sa,
)

__all__ = [
    'PhoneNumberError',
    'PhoneNumberInvalidError',
    'PhoneNumberBlockedError',
    'PhoneNumberInUseError',
    'parse_phone_number',
    'validate_phone_number',
    'canonical_phone_number',
    'phone_blake2b160_hash',
    'PhoneNumber',
    'PhoneNumberMixin',
]

# --- Enums and constants --------------------------------------------------------------


# Unprefixed phone numbers are assumed to be a local number in India (+91). A fallback
# lookup to US numbers (+1) used to be performed but was removed in #1436 because:
# 1. Both regions have 10 digit local numbers,
# 2. Indian numbers have clear separation between SMS-capable and incapable numbers, but
# 3. US numbers may be mobile or fixed, with unknown SMS capability, and therefore
# 4. In practice, we received too many random numbers that looked legit but were junk.
PHONE_LOOKUP_REGIONS = ['IN']


# --- Exceptions -----------------------------------------------------------------------


class PhoneNumberError(ValueError):
    """Base class for PhoneNumber exceptions."""


class PhoneNumberInvalidError(PhoneNumberError):
    """Not a phone number."""


class PhoneNumberBlockedError(PhoneNumberError):
    """Phone number is blocked from use."""


class PhoneNumberInUseError(PhoneNumberError):
    """Phone number is in use by another owner."""


# --- Utilities ------------------------------------------------------------------------


# Three phone number utilities are presented here. All three return a formatted phone
# number in E164 format.
#
# 1. :func:`parse_phone_number` attempts to find a valid phone number in the given input
#    and optionally validates it for SMS support. SMS validation uses a static database
#    supplied by Google's libphonenumber, which cannot distinguish between mobile and
#    fixed line in the US, so an additional live database may be needed there. This
#    function is meant for parsing phone numbers in UI forms.
#
# 2. :func:`validate_phone_number` expects an international phone number and will
#    validate it to be a real number (as per Google's libphonenumber). This function is
#    meant for sanity check before making a new database entry. Returns a formatted
#    number, or raises :exc:`PhoneNumberInvalidError`.
#
# 3. :func:`canonical_phone_number` will not attempt validation, only applying E164
#    formatting. However, if a number cannot be recognised, it will raise
#    :exc:`PhoneNumberInvalidError`.


@overload
def parse_phone_number(candidate: str) -> Optional[str]:
    ...


@overload
def parse_phone_number(candidate: str, sms: Literal[False]) -> Optional[str]:
    ...


@overload
def parse_phone_number(
    candidate: str, sms: Literal[False], parsed: Literal[True]
) -> Optional[phonenumbers.PhoneNumber]:
    ...


@overload
def parse_phone_number(
    candidate: str, sms: Union[bool, Literal[True]]
) -> Optional[Union[str, Literal[False]]]:
    ...


@overload
def parse_phone_number(
    candidate: str,
    sms: Union[bool, Literal[True]],
    parsed: Literal[True],
) -> Optional[Union[phonenumbers.PhoneNumber, Literal[False]]]:
    ...


@overload
def parse_phone_number(
    candidate: str,
    sms: Union[bool, Literal[True]],
    parsed: Union[bool, Literal[False]],
) -> Optional[Union[phonenumbers.PhoneNumber, Literal[False]]]:
    ...


def parse_phone_number(
    candidate: str, sms: bool = False, parsed: bool = False
) -> Optional[Union[str, phonenumbers.PhoneNumber, Literal[False]]]:
    """
    Attempt to parse and validate a phone number and return in E164 format.

    If the number is not in international format, it will be validated for common
    regions as listed in :attr:`PHONE_LOOKUP_REGIONS` (currently only India).

    :param sms: Validate that the number is from a range that supports SMS delivery,
        returning `False` if it isn't

    :returns: E164-formatted phone number if found and valid, `None` if not found, or
        `False` if the number is valid but does not support SMS delivery
    """
    # Assume unprefixed numbers to be a local number in one of the supported common
    # regions. We start with the higher priority home region and return the _first_
    # candidate that is likely to be a valid number. This behaviour differentiates it
    # from similar code in :func:`~funnel.models.utils.getuser`, where the loop exits
    # with the _last_ valid candidate (as it's coupled with a
    # :class:`~funnel.models.user.AccountPhone` lookup)
    sms_invalid = False
    try:
        for region in PHONE_LOOKUP_REGIONS:
            parsed_number = phonenumbers.parse(candidate, region)
            if phonenumbers.is_valid_number(parsed_number):
                if sms:
                    if phonenumbers.number_type(parsed_number) not in (
                        phonenumbers.PhoneNumberType.MOBILE,
                        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
                    ):
                        sms_invalid = True
                        continue  # Not valid for SMS, continue searching regions
                if parsed:
                    return parsed_number
                return phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
    except phonenumbers.NumberParseException:
        pass
    # We found a number that is valid, but the caller wanted it to be valid for SMS and
    # it isn't, so return a special flag
    if sms_invalid:
        return False
    return None


def validate_phone_number(candidate: Union[str, phonenumbers.PhoneNumber]) -> str:
    """
    Validate an international phone number and return in E164 format.

    :raises: PhoneNumberInvalidError if format is invalid
    """
    if not isinstance(candidate, phonenumbers.PhoneNumber):
        try:
            parsed_number = phonenumbers.parse(candidate)
        except phonenumbers.NumberParseException as exc:
            raise PhoneNumberInvalidError(f"Not a phone number: {candidate}") from exc
    else:
        parsed_number = candidate
    if phonenumbers.is_valid_number(parsed_number):
        return phonenumbers.format_number(
            parsed_number, phonenumbers.PhoneNumberFormat.E164
        )
    raise PhoneNumberInvalidError(f"Not a valid phone number: {candidate}")


def canonical_phone_number(candidate: Union[str, phonenumbers.PhoneNumber]) -> str:
    """Normalize an international phone number by rendering in E164 format."""
    if not isinstance(candidate, phonenumbers.PhoneNumber):
        try:
            candidate = phonenumbers.parse(candidate)
        except phonenumbers.NumberParseException as exc:
            raise PhoneNumberInvalidError(f"Not a phone number: {candidate}") from exc
    return phonenumbers.format_number(candidate, phonenumbers.PhoneNumberFormat.E164)


def phone_blake2b160_hash(
    phone: Union[str, phonenumbers.PhoneNumber],
    *,
    _pre_validated_formatted: bool = False,
) -> bytes:
    """BLAKE2b hash of the given phone number using digest size 20 (160 bits)."""
    if not _pre_validated_formatted or isinstance(phone, phonenumbers.PhoneNumber):
        number = canonical_phone_number(phone)
    else:
        number = phone
    return hashlib.blake2b(number.encode('utf-8'), digest_size=20).digest()


# --- Models ---------------------------------------------------------------------------


class PhoneNumber(BaseMixin, db.Model):  # type: ignore[name-defined]
    """
    Represents a phone number as a standalone entity, with associated metadata.

    Prior to this model, phone numbers were stored in the
    :class:`~funnel.models.user.AccountPhone` and
    :class:`~funnel.models.notification.SmsMessage models, with no ability to store
    preferences against a number, such as enforcing a block list or scraping against
    mobile number revocation lists.

    This model replicates the idea and implementation of the
    :class:`~funnel.models.phone_number.PhoneNumber` model.

    New phone numbers must be added using the :meth:`add` or :meth:`add_for`
    classmethods, depending on whether the phone number is linked to an owner or not.
    """

    __tablename__ = 'phone_number'
    __allow_unmapped__ = True

    #: Backrefs to this model from other models, populated by :class:`PhoneNumberMixin`
    #: Contains the name of the relationship in the :class:`PhoneNumber` model
    __backrefs__: Set[str] = set()
    #: These backrefs claim exclusive use of the phone number for their linked owner.
    #: See :class:`PhoneNumberMixin` for implementation detail
    __exclusive_backrefs__: Set[str] = set()

    #: The phone number, centrepiece of this model. Stored normalized in E164 format.
    #: Validated by the :func:`_validate_phone` event handler
    number = sa.Column(sa.Unicode, nullable=True, unique=True)

    #: BLAKE2b 160-bit hash of :attr:`phone`. Kept permanently even if phone is
    #: removed. SQLAlchemy type LargeBinary maps to PostgreSQL BYTEA. Despite the name,
    #: we're only storing 20 bytes
    blake2b160 = immutable(
        sa.Column(
            sa.LargeBinary,
            sa.CheckConstraint(
                'LENGTH(blake2b160) = 20',
                name='phone_number_blake2b160_check',
            ),
            nullable=False,
            unique=True,
        )
    )

    # Flags and timestamps for messaging activity. Since a delivery failure can happen
    # anywhere in the chain, from sender-side failure to carrier block to an unreachable
    # device, we record distinct timestamps for last sent, delivery and failure.

    #: Cached state for whether this phone number is known to have SMS support
    has_sms = sa.Column(sa.Boolean, nullable=True)
    #: Timestamp at which this number was determined to be valid/invalid for SMS
    has_sms_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    #: Cached state for whether this phone number is known to be on WhatsApp or not
    has_wa = sa.Column(sa.Boolean, nullable=True)
    #: Timestamp at which this number was tested for availability on WhatsApp
    has_wa_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    #: Timestamp of last SMS sent
    msg_sms_sent_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    #: Timestamp of last SMS delivered
    msg_sms_delivered_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    #: Timestamp of last SMS delivery failure
    msg_sms_failed_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    #: Timestamp of last WA message sent
    msg_wa_sent_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    #: Timestamp of last WA message delivered
    msg_wa_delivered_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    #: Timestamp of last WA message delivery failure
    msg_wa_failed_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    #: Timestamp of last known recipient activity resulting from sent messages
    active_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    #: Is this phone number blocked from being used? :attr:`phone` should be null if so.
    blocked_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        # If `blocked_at` is not None, `number` and `has_*` must be None
        sa.CheckConstraint(
            sa.or_(  # type: ignore[arg-type]
                blocked_at.is_(None),  # or...
                sa.and_(
                    blocked_at.isnot(None),
                    number.is_(None),
                    has_sms.is_(None),
                    has_sms_at.is_(None),
                    has_wa.is_(None),
                    has_wa_at.is_(None),
                ),
            ),
            'phone_number_blocked_check',
        ),
        sa.CheckConstraint(
            sa.or_(
                sa.and_(has_sms.is_(None), has_sms_at.is_(None)),
                sa.and_(has_sms.isnot(None), has_sms_at.isnot(None)),
            ),
            'phone_number_has_sms_check',
        ),
        sa.CheckConstraint(
            sa.or_(
                sa.and_(has_wa.is_(None), has_wa_at.is_(None)),
                sa.and_(has_wa.isnot(None), has_wa_at.isnot(None)),
            ),
            'phone_number_has_wa_check',
        ),
    )

    def __init__(self, phone: str, *, _pre_validated_formatted: bool = False) -> None:
        if not isinstance(phone, str):
            raise ValueError("A string phone number is required")
        if not _pre_validated_formatted:
            number = validate_phone_number(phone)
        else:
            number = phone
        # Set the hash first so the phone column validator passes.
        self.blake2b160 = phone_blake2b160_hash(number, _pre_validated_formatted=True)
        self.number = number

    def __str__(self) -> str:
        """Cast :class:`PhoneNumber` into a string."""
        return self.number or ''

    def __repr__(self) -> str:
        """Debugging representation of :class:`PhoneNumber`."""
        if self.number:
            return f'PhoneNumber({self.number!r})'
        return f'PhoneNumber(blake2b160={self.blake2b160!r})'

    @hybrid_property
    def is_blocked(self) -> bool:
        """
        Read-only flag indicating this phone number is blocked from use.

        To set this flag, call :classmethod:`mark_blocked` using the phone number.
        """
        with db.session.no_autoflush:
            return self.blocked_at is not None

    @is_blocked.expression
    def is_blocked(cls):  # pylint: disable=no-self-argument
        """Expression form of is_blocked check."""
        return cls.blocked_at.isnot(None)

    @with_roles(read={'all'})
    @cached_property
    def phone_hash(self) -> str:
        """Public identifier string for this phone number, usable in URLs."""
        return base58.b58encode(self.blake2b160).decode()

    # Compatibility name for notifications framework
    transport_hash = phone_hash

    @with_roles(call={'all'})
    def md5(self) -> Optional[str]:
        """MD5 hash of :attr:`phone`, for legacy use only."""
        # TODO: After upgrading to Python 3.9, use usedforsecurity=False
        return (
            hashlib.md5(  # nosec  # skipcq: PTC-W1003
                self.number.encode('utf-8')
            ).hexdigest()
            if self.number
            else None
        )

    @cached_property
    def parsed(self) -> Optional[phonenumbers.PhoneNumber]:
        """Return parsed phone number using libphonenumbers."""
        if self.number:
            return phonenumbers.parse(self.number)
        return None

    @cached_property
    def formatted(self) -> str:
        """Return a phone number formatted for user display."""
        parsed = self.parsed
        if parsed is not None:
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
        if self.is_blocked:  # pylint: disable=using-constant-test
            return _('[blocked]')
        return _('[removed]')

    def is_exclusive(self) -> bool:
        """Return True if this PhoneNumber is in an exclusive relationship."""
        return any(
            related_obj
            for backref_name in self.__exclusive_backrefs__
            for related_obj in getattr(self, backref_name)
        )

    def is_available_for(self, owner: object) -> bool:
        """Return True if this PhoneNumber is available for the given owner."""
        for backref_name in self.__exclusive_backrefs__:
            for related_obj in getattr(self, backref_name):
                curr_owner = getattr(related_obj, related_obj.__phone_for__)
                if curr_owner is not None and curr_owner != owner:
                    return False
        return True

    def refcount(self) -> int:
        """Count of references to this :class:`PhoneNumber` instance."""
        # obj.phone_number_reference_is_active is a bool, but int(bool) is 0 or 1
        return sum(
            sum(
                obj.phone_number_reference_is_active
                for obj in getattr(self, backref_name)
            )
            for backref_name in self.__backrefs__
        )

    def mark_has_sms(self, value: bool) -> None:
        """Mark this phone number as having SMS capability (or not)."""
        self.has_sms = value
        self.has_sms_at = sa.func.utcnow()

    def mark_has_wa(self, value: bool) -> None:
        """Mark this phone number has having WhatsApp capability (or not)."""
        self.has_wa = value
        self.has_wa_at = sa.func.utcnow()

    def mark_active(self, sms: bool = False, wa: bool = False) -> None:
        """
        Mark phone number as active.

        Optionally, indicate if activity was observed through a specific application,
        confirming the availability of this phone number under that application.

        :param sms: Activity was observed via SMS
        :param wa: Activity was observed via WhatsApp
        """
        self.active_at = sa.func.utcnow()
        if sms:
            self.mark_has_sms(True)
        if wa:
            self.mark_has_wa(True)

    def mark_forgotten(self) -> None:
        """Forget this phone number."""
        self.number = None
        self.has_sms = None
        self.has_sms_at = None
        self.has_wa = None
        self.has_wa_at = None

    def mark_blocked(self) -> None:
        """Mark phone number as blocked and forgotten."""
        self.mark_forgotten()
        self.blocked_at = sa.func.utcnow()

    def mark_unblocked(self, phone: str) -> None:
        """Mark phone number as unblocked by providing the phone number."""
        self.number = phone  # This will go to the validator to compare against the hash
        self.blocked_at = None

    @overload
    @classmethod
    def get_filter(
        cls, *, phone: Union[str, phonenumbers.PhoneNumber]
    ) -> Optional[ColumnElement]:
        ...

    @overload
    @classmethod
    def get_filter(cls, *, blake2b160: bytes) -> ColumnElement:
        ...

    @overload
    @classmethod
    def get_filter(cls, *, phone_hash: str) -> ColumnElement:
        ...

    @overload
    @classmethod
    def get_filter(
        cls,
        *,
        phone: Optional[Union[str, phonenumbers.PhoneNumber]],
        blake2b160: Optional[bytes],
        phone_hash: Optional[str],
    ) -> Optional[ColumnElement]:
        ...

    @classmethod
    def get_filter(
        cls,
        *,
        phone: Optional[Union[str, phonenumbers.PhoneNumber]] = None,
        blake2b160: Optional[bytes] = None,
        phone_hash: Optional[str] = None,
    ) -> Optional[ColumnElement]:
        """
        Get an filter condition for retriving a :class:`PhoneNumber`.

        Accepts a normalized phone number or a blake2b160 hash in either bytes or base58
        form. Internally converts all lookups to a bytes-based hash lookup. Returns an
        expression suitable for use as a query filter.
        """
        require_one_of(phone=phone, blake2b160=blake2b160, phone_hash=phone_hash)
        if phone:
            blake2b160 = phone_blake2b160_hash(phone)
        elif phone_hash:
            blake2b160 = base58.b58decode(phone_hash)

        return cls.blake2b160 == blake2b160

    @overload
    @classmethod
    def get(
        cls,
        phone: Union[str, phonenumbers.PhoneNumber],
        *,
        is_blocked: Optional[bool] = None,
    ) -> Optional[PhoneNumber]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        blake2b160: bytes,
        is_blocked: Optional[bool] = None,
    ) -> Optional[PhoneNumber]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        phone_hash: str,
        is_blocked: Optional[bool] = None,
    ) -> Optional[PhoneNumber]:
        ...

    @classmethod
    def get(
        cls,
        phone: Optional[Union[str, phonenumbers.PhoneNumber]] = None,
        *,
        blake2b160: Optional[bytes] = None,
        phone_hash: Optional[str] = None,
        is_blocked: Optional[bool] = None,
    ) -> Optional[PhoneNumber]:
        """
        Get an :class:`PhoneNumber` instance by normalized phone number or its hash.

        Internally converts an number lookup into a hash-based lookup.
        """
        try:
            query = cls.query.filter(
                cls.get_filter(
                    phone=phone, blake2b160=blake2b160, phone_hash=phone_hash
                )
            )
        except PhoneNumberInvalidError:
            return None  # phone number was not valid
        if is_blocked is not None:
            if is_blocked:
                query = query.filter(cls.blocked_at.isnot(None))
            else:
                query = query.filter(cls.blocked_at.is_(None))
        return query.one_or_none()

    @classmethod
    def add(cls, phone: Union[str, phonenumbers.PhoneNumber]) -> PhoneNumber:
        """
        Create a new :class:`PhoneNumber` after normalization and validation.

        Raises an exception if the number is blocked from use, or if the phone number
        is not valid as per Google's libphonenumber validator.

        :raises ValueError: If phone number is not valid
        :raises PhoneNumberBlockedError: If phone number is blocked
        """
        number = validate_phone_number(phone)

        existing = cls.get(number)
        if existing is not None:
            if existing.is_blocked:
                raise PhoneNumberBlockedError("Phone number is blocked")
            # Restore the phone column if it's not present. Do not modify it otherwise
            if not existing.number:
                existing.number = number
            return existing
        new_phone = PhoneNumber(number, _pre_validated_formatted=True)
        db.session.add(new_phone)
        return new_phone

    @classmethod
    def add_for(
        cls, owner: Optional[object], phone: Union[str, phonenumbers.PhoneNumber]
    ) -> PhoneNumber:
        """
        Create a new :class:`PhoneNumber` after validation.

        Unlike :meth:`add`, this one requires the phone number to not be in an
        exclusive relationship with another owner.

        :raises ValueError: If phone number syntax is invalid
        :raises PhoneNumberBlockedError: If phone number is blocked
        """
        number = validate_phone_number(phone)

        existing = cls.get(number)
        if existing is not None:
            if not existing.is_available_for(owner):
                raise PhoneNumberInUseError("This phone number is in use")
            # No exclusive lock found? Let it be used then
            existing.number = number  # In case it was nulled earlier
            return existing
        new_phone = PhoneNumber(number, _pre_validated_formatted=True)
        db.session.add(new_phone)
        return new_phone

    @classmethod
    def validate_for(
        cls,
        owner: Optional[object],
        phone: Union[str, phonenumbers.PhoneNumber],
        new: bool = False,
    ) -> Union[bool, Literal['invalid', 'not_new', 'blocked']]:
        """
        Validate whether the phone number is available to the given owner.

        Returns False if the number is blocked or in use by another owner, True if
        available without issues, or a string value indicating the concern:

        1. 'not_new': Phone number is already attached to owner (if `new` is True)
        2. 'invalid': Invalid syntax and therefore unusable
        3. 'blocked': Phone number has been blocked from use

        :param owner: Proposed owner of this phone number (may be None)
        :param phone: Phone number to validate
        :param new: Fail validation if phone number is already in use by owner
        """
        try:
            phone = validate_phone_number(phone)
        except PhoneNumberInvalidError:
            return 'invalid'
        existing = cls.get(phone)
        if existing is None:
            return True
        # There's an existing? Is it blocked?
        if existing.is_blocked:
            return 'blocked'
        # Is the existing phone mumber available for this owner?
        if not existing.is_available_for(owner):
            # Not available, so return False
            return False
        # Caller is asking to confirm this is not already belonging to this owner
        if new and existing.is_exclusive():
            # It's in an exclusive relationship, and we're already determined it's
            # available to this owner, so it must be exclusive to them
            return 'not_new'
        return True


@declarative_mixin
class PhoneNumberMixin:
    """
    Mixin class for models that refer to :class:`PhoneNumber`.

    Subclasses should set configuration using the four ``__phone_*__`` attributes and
    should optionally override :meth:`phone_number_reference_is_active` if the model
    implements archived rows, such as in memberships.
    """

    # Provided by subclasses
    __tablename__: str

    #: This class has an optional dependency on PhoneNumber
    __phone_optional__: bool = True
    #: This class has a unique constraint on the fkey to PhoneNumber
    __phone_unique__: bool = False
    #: A relationship from this model is for the (single) owner at this attr
    __phone_for__: Optional[str] = None
    #: If `__phone_for__` is specified and this flag is True, the phone number is
    #: considered exclusive to this owner and may not be used by any other owner
    __phone_is_exclusive__: bool = False

    @declared_attr
    @classmethod
    def phone_number_id(cls) -> Mapped[int]:
        """Foreign key to phone_number table."""
        return sa.Column(
            sa.Integer,
            sa.ForeignKey('phone_number.id', ondelete='SET NULL'),
            nullable=cls.__phone_optional__,
            unique=cls.__phone_unique__,
            index=not cls.__phone_unique__,
        )

    @declared_attr
    def phone_number(  # pylint: disable=no-self-argument
        cls,
    ) -> Mapped[PhoneNumber]:
        """Instance of :class:`PhoneNumber` as a relationship."""
        backref_name = 'used_in_' + cls.__tablename__
        PhoneNumber.__backrefs__.add(backref_name)
        if cls.__phone_for__ and cls.__phone_is_exclusive__:
            PhoneNumber.__exclusive_backrefs__.add(backref_name)
        return sa.orm.relationship(PhoneNumber, backref=backref_name)

    @property
    def phone(self) -> Optional[str]:
        """
        Shorthand for ``self.phone_number.number``.

        Setting a value does the equivalent of one of these, depending on whether
        the object requires the phone number to be available to its owner::

            self.phone_number = PhoneNumber.add(phone)
            self.phone_number = PhoneNumber.add_for(owner, phone)

        Where the owner is found from the attribute named in `cls.__phone_for__`.
        """
        if self.phone_number:
            return self.phone_number.number
        return None

    @phone.setter
    def phone(self, value: Optional[str]) -> None:
        if self.__phone_for__:
            if value is not None:
                self.phone_number = PhoneNumber.add_for(
                    getattr(self, self.__phone_for__), value
                )
            else:
                self.phone_number = None
        else:
            if value is not None:
                self.phone_number = PhoneNumber.add(value)
            else:
                self.phone_number = None

    @property
    def phone_number_reference_is_active(self) -> bool:
        """
        Assert that the reference to an phone number is valid, requiring it to be kept.

        Subclasses should override to return `False` if they hold inactive references
        and approve of the phone number being forgotten.
        """
        return True

    @property
    def transport_hash(self) -> Optional[str]:
        """Phone hash using the compatibility name for notifications framework."""
        return (
            self.phone_number.phone_hash
            if self.phone_number  # pylint: disable=using-constant-test
            else None
        )


def _clear_cached_properties(target: PhoneNumber) -> None:
    """Clear cached properties in :class:`PhoneNumber`."""
    for attr in ('parsed', 'formatted'):
        try:
            delattr(target, attr)
        except KeyError:
            # cached_property raises KeyError when there's no existing cached value
            pass


@event.listens_for(PhoneNumber.number, 'set', retval=True)
def _validate_number(target: PhoneNumber, value: Any, old_value: Any, initiator) -> Any:
    # First: check if value is acceptable and phone attribute can be set
    if not value and value is not None:
        # Only `None` is an acceptable falsy value
        raise ValueError("A phone number is required")
    if old_value == value:
        # Old value is new value. Do nothing. Return without validating
        return value
    if old_value is NO_VALUE and inspect(target).has_identity is False:
        # Old value is unknown and target is a transient object. Continue
        pass
    elif value is None:
        # Caller is trying to unset phone. Allow this
        pass
    elif old_value is None:
        # Caller is trying to restore phone. Allow but validate match for existing hash
        pass
    else:
        # Under any other condition, phone number is immutable
        raise ValueError("Phone number cannot be changed or reformatted")

    # All clear? Now check against the hash
    if value is not None and isinstance(value, str):
        value = canonical_phone_number(value)
        hashed = phone_blake2b160_hash(value, _pre_validated_formatted=True)
        if hashed != target.blake2b160:
            raise ValueError("Phone number does not match existing blake2b160 hash")
        _clear_cached_properties(target)
        return value
    if value is None:
        # Allow removing phone (we still keep the hash), but clear cached properties
        _clear_cached_properties(target)
        return value
    raise ValueError(f"Invalid value for phone number: {value}")


def _send_refcount_event_remove(target, value, initiator):
    phonenumber_refcount_dropping.send(target)


def _send_refcount_event_before_delete(mapper_, connection, target):
    if target.phone_number:
        phonenumber_refcount_dropping.send(target.phone_number)


@event.listens_for(mapper, 'after_configured')
def _setup_refcount_events() -> None:
    for backref_name in PhoneNumber.__backrefs__:
        attr = getattr(PhoneNumber, backref_name)
        event.listen(attr, 'remove', _send_refcount_event_remove)


def _phone_number_mixin_set_validator(
    target, value: Optional[PhoneNumber], old_value, initiator
) -> None:
    if value is not None and value != old_value and target.__phone_for__:
        if value.is_blocked:
            raise PhoneNumberBlockedError("This phone number has been blocked")
        if not value.is_available_for(getattr(target, target.__phone_for__)):
            raise PhoneNumberInUseError("This phone number it not available")


@event.listens_for(PhoneNumberMixin, 'mapper_configured', propagate=True)
def _phone_number_mixin_configure_events(mapper_, cls: PhoneNumberMixin):
    event.listen(cls.phone_number, 'set', _phone_number_mixin_set_validator)
    event.listen(cls, 'before_delete', _send_refcount_event_before_delete)
