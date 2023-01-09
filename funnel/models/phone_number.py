"""Phone number model, storing a number distinct from its uses."""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Optional, Set, Union, overload
import hashlib

from sqlalchemy import event, inspect
from sqlalchemy.orm import mapper
from sqlalchemy.orm.attributes import NO_VALUE
from sqlalchemy.sql.expression import ColumnElement

from werkzeug.utils import cached_property

import base58

from coaster.sqlalchemy import auto_init_default, immutable, with_roles
from coaster.utils import require_one_of

from ..signals import phonenumber_refcount_dropping
from ..typing import Mapped
from ..utils import validate_format_phone_number
from . import BaseMixin, db, declarative_mixin, declared_attr, hybrid_property, sa

__all__ = [
    'PhoneNumberError',
    'PhoneNumberBlockedError',
    'PhoneNumberInUseError',
    'PhoneDeliveryState',
    'phone_blake2b160_hash',
    'PhoneNumber',
    'PhoneNumberMixin',
]


class PhoneNumberError(ValueError):
    """Base class for PhoneNumber exceptions."""


class PhoneNumberBlockedError(PhoneNumberError):
    """Phone number is blocked from use."""


class PhoneNumberInUseError(PhoneNumberError):
    """Phone number is in use by another owner."""


class PhoneDeliveryState(IntEnum):
    """Delivery reports for text messages (SMS) to a phone number."""

    UNKNOWN = 1
    SENT = 2
    DELIVERED = 3
    UNREACHABLE = 4


def phone_blake2b160_hash(
    phone: str, *, _pre_validated_formatted: bool = False
) -> bytes:
    """BLAKE2b hash of the given phone number using digest size 20 (160 bits)."""
    number: Optional[str]
    if not _pre_validated_formatted:
        number = validate_format_phone_number(phone)
    else:
        number = phone
    return hashlib.blake2b(number.encode('utf-8'), digest_size=20).digest()


class PhoneNumber(BaseMixin, db.Model):  # type: ignore[name-defined]
    """
    Represents a phone number as a standalone entity, with associated metadata.

    Prior to this model, phone numbers were stored in the
    :class:`~funnel.models.user.UserPhone` and
    :class:`~funnel.models.notification.SmsMessage models, with no ability to store
    preferences against a number, such as enforcing a block list or scraping against
    mobile number revocation lists.

    This model replicates the idea and implementation of the
    :class:`~funnel.models.phone_number.PhoneNumber` model.

    New phone numbers must be added using the :meth:`add` or :meth:`add_for`
    classmethods, depending on whether the phone number is linked to an owner or not.
    """

    __tablename__ = 'phone_number'

    #: Backrefs to this model from other models, populated by :class:`PhoneNumberMixin`
    #: Contains the name of the relationship in the :class:`PhoneNumber` model
    __backrefs__: Set[str] = set()
    #: These backrefs claim exclusive use of the phone number for their linked owner.
    #: See :class:`PhoneNumberMixin` for implementation detail
    __exclusive_backrefs__: Set[str] = set()

    #: The phone number, centrepiece of this model. Stored normalized in E164 format.
    #: Validated by the :func:`_validate_phone` event handler
    phone = sa.Column(sa.Unicode, nullable=True, index=True)

    #: BLAKE2b 160-bit hash of :attr:`phone`. Kept permanently even if phone is
    #: removed. SQLAlchemy type LargeBinary maps to PostgreSQL BYTEA. Despite the name,
    #: we're only storing 20 bytes
    blake2b160 = immutable(
        sa.Column(
            sa.LargeBinary,
            sa.CheckConstraint('length(blake2b160) = 20'),
            nullable=False,
            unique=True,
        )
    )

    #: Does this phone number work? Records last known delivery state
    _delivery_state = sa.Column(
        'delivery_state',
        sa.Integer,
        sa.CheckConstraint(
            f'delivery_state IN ('
            f'{", ".join(str(int(_e)) for _e in PhoneDeliveryState)}'
            f')'
        ),
        default=PhoneDeliveryState.UNKNOWN,
    )
    # delivery_state = StateManager(
    #     '_delivery_state',
    #     PhoneDeliveryState,
    #     doc="Last known delivery state of this phone number",
    # )
    #: Timestamp of last known delivery state
    delivery_state_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )
    #: Timestamp of last known recipient activity resulting from sent messages
    active_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    #: Is this phone number blocked from being used? If so, :attr:`phone` should be
    #: null.
    _is_blocked = sa.Column('is_blocked', sa.Boolean, nullable=False, default=False)

    __table_args__ = (
        # If `is_blocked` is True, `phone`  must be None
        sa.CheckConstraint(
            sa.or_(  # type: ignore[arg-type]
                _is_blocked.isnot(True),
                sa.and_(_is_blocked.is_(True), phone.is_(None)),
            ),
            'phone_number_phone_is_blocked_check',
        ),
    )

    @hybrid_property
    def is_blocked(self) -> bool:
        """
        Read-only flag indicating this phone number is blocked from use.

        To set this flag, call :classmethod:`mark_blocked` using the phone number.
        """
        with db.session.no_autoflush:
            return self._is_blocked

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
                self.phone.encode('utf-8')
            ).hexdigest()
            if self.phone
            else None
        )

    def __str__(self) -> str:
        """Cast phone number into a string."""
        return self.phone or ''

    def __repr__(self) -> str:
        """Debugging representation of the phone number."""
        return f'PhoneNumber({self.phone!r})'

    def __init__(self, phone: str, *, _pre_validated_formatted: bool = False) -> None:
        if not isinstance(phone, str):
            raise ValueError("A string phone number is required")
        if not _pre_validated_formatted:
            number = validate_format_phone_number(phone)
        else:
            number = phone
        # Set the hash first so the phone column validator passes.
        self.blake2b160 = phone_blake2b160_hash(number, _pre_validated_formatted=True)
        self.phone = number

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

    def mark_blocked(self) -> None:
        """Mark phone number as blocked."""
        self.phone = None
        self._is_blocked = True

    @overload
    @classmethod
    def get_filter(cls, *, phone: str) -> Optional[ColumnElement]:
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
        phone: Optional[str],
        blake2b160: Optional[bytes],
        phone_hash: Optional[str],
    ) -> Optional[ColumnElement]:
        ...

    @classmethod
    def get_filter(
        cls,
        *,
        phone: Optional[str] = None,
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
        phone: str,
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
        phone: Optional[str] = None,
        *,
        blake2b160: Optional[bytes] = None,
        phone_hash: Optional[str] = None,
        is_blocked: Optional[bool] = None,
    ) -> Optional[PhoneNumber]:
        """
        Get an :class:`PhoneNumber` instance by normalized phone number or its hash.

        Internally converts an number lookup into a hash-based lookup.
        """
        query = cls.query.filter(
            cls.get_filter(phone=phone, blake2b160=blake2b160, phone_hash=phone_hash)
        )
        if is_blocked is not None:
            query = query.filter_by(_is_blocked=is_blocked)
        return query.one_or_none()

    @classmethod
    def add(cls, phone: str) -> PhoneNumber:
        """
        Create a new :class:`PhoneNumber` after normalization and validation.

        Raises an exception if the number is blocked from use, or if the phone number
        is not valid as per Google's libphonenumber validator.

        :raises ValueError: If phone number is not valid
        :raises PhoneNumberBlockedError: If phone number is blocked
        """
        number = validate_format_phone_number(phone)

        existing = cls.get(number)
        if existing is not None:
            if existing.is_blocked:
                raise PhoneNumberBlockedError("Phone number is blocked")
            # Restore the phone column if it's not present. Do not modify it otherwise
            if not existing.phone:
                existing.phone = number
            return existing
        new_phone = PhoneNumber(number, _pre_validated_formatted=True)
        db.session.add(new_phone)
        return new_phone

    @classmethod
    def add_for(cls, owner: Optional[object], phone: str) -> PhoneNumber:
        """
        Create a new :class:`PhoneNumber` after validation.

        Unlike :meth:`add`, this one requires the phone number to not be in an
        exclusive relationship with another owner.

        :raises ValueError: If phone number syntax is invalid
        :raises PhoneNumberBlockedError: If phone number is blocked
        """
        number = validate_format_phone_number(phone)

        existing = cls.get(number)
        if existing is not None:
            if not existing.is_available_for(owner):
                raise PhoneNumberInUseError("This phone number is in use")
            # No exclusive lock found? Let it be used then
            existing.phone = number  # In case it was nulled earlier
            return existing
        new_phone = PhoneNumber(number, _pre_validated_formatted=True)
        db.session.add(new_phone)
        return new_phone

    @classmethod
    def validate_for(
        cls,
        owner: Optional[object],
        phone: str,
        new: bool = False,
    ) -> Union[bool, str]:
        """
        Validate whether the phone number is available to the given owner.

        Returns False if the number is blocked or in use by another owner, True if
        available without issues, or a string value indicating the concern:

        1. 'not_new': Phone number is already attached to owner (if `new` is True)
        2. 'invalid': Invalid syntax and therefore unusable

        :param owner: Proposed owner of this phone number (may be None)
        :param str phone: Phone number to validate
        :param bool new: Fail validation if phone number is already in use
        """
        try:
            phone = validate_format_phone_number(phone)
        except ValueError:
            return 'invalid'
        existing = cls.get(phone)
        if existing is None:
            return True
        # There's an existing? Is it blocked?
        if existing.is_blocked:
            return False
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
    def phone_number_id(  # pylint: disable=no-self-argument
        cls,
    ) -> sa.Column[int]:
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
    ) -> sa.orm.relationship[PhoneNumber]:
        """Instance of :class:`PhoneNumber` as a relationship."""
        backref_name = 'used_in_' + cls.__tablename__
        PhoneNumber.__backrefs__.add(backref_name)
        if cls.__phone_for__ and cls.__phone_is_exclusive__:
            PhoneNumber.__exclusive_backrefs__.add(backref_name)
        return sa.orm.relationship(PhoneNumber, backref=backref_name)

    @declared_attr
    def phone(cls) -> Mapped[Optional[str]]:  # pylint: disable=no-self-argument
        """Shorthand for ``self.phone_number.phone``."""

        def phone_get(self) -> Optional[str]:
            """
            Shorthand for ``self.phone_number.phone``.

            Setting a value does the equivalent of one of these, depending on whether
            the object requires the phone number to be available to its owner::

                self.phone_number = PhoneNumber.add(phone)
                self.phone_number = PhoneNumber.add_for(owner, phone)

            Where the owner is found from the attribute named in `cls.__phone_for__`.
            """
            if self.phone_number:
                return self.phone_number.phone
            return None

        if cls.__phone_for__:

            def phone_set(self, value):
                if value is not None:
                    self.phone_number = PhoneNumber.add_for(
                        getattr(self, cls.__phone_for__), value
                    )
                else:
                    self.phone_number = None

        else:

            def phone_set(self, value):
                if value is not None:
                    self.phone_number = PhoneNumber.add(value)
                else:
                    self.phone_number = None

        return property(fget=phone_get, fset=phone_set)

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


auto_init_default(PhoneNumber._delivery_state)  # pylint: disable=protected-access
auto_init_default(PhoneNumber.delivery_state_at)
auto_init_default(PhoneNumber._is_blocked)  # pylint: disable=protected-access


@event.listens_for(PhoneNumber.phone, 'set', retval=True)
def _validate_phone(target, value: Any, old_value: Any, initiator) -> Any:
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
        value = validate_format_phone_number(value)
        hashed = phone_blake2b160_hash(value, _pre_validated_formatted=True)
        if hashed != target.blake2b160:
            raise ValueError("Phone number does not match existing blake2b160 hash")
        return value
    if value is None:
        # Allow removing phone (we still keep the hash)
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
    if value != old_value and target.__phone_for__:
        if value is not None:
            if value.is_blocked:
                raise PhoneNumberBlockedError("This phone number has been blocked")
            if not value.is_available_for(getattr(target, target.__phone_for__)):
                raise PhoneNumberInUseError("This phone number it not available")


@event.listens_for(PhoneNumberMixin, 'mapper_configured', propagate=True)
def _phone_number_mixin_configure_events(
    mapper_,
    cls: db.Model,  # type: ignore[name-defined]
):
    event.listen(cls.phone_number, 'set', _phone_number_mixin_set_validator)
    event.listen(cls, 'before_delete', _send_refcount_event_before_delete)
