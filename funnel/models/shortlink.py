"""Shortlink models."""

from __future__ import annotations

import hashlib
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Iterable
from os import urandom
from typing import Literal, overload

from furl import furl
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import Comparator

from coaster.sqlalchemy import immutable, with_roles

from .account import Account
from .base import (
    Mapped,
    Model,
    NoIdMixin,
    UrlType,
    db,
    hybrid_property,
    relationship,
    sa,
    sa_orm,
)
from .helpers import profanity

__all__ = ['Shortlink']


# MARK: Constants ----------------------------------------------------------------------

#: Size for for SMS and other length-sensitive uses. This can be raised from 3 to 4
#: bytes as usage grows
SHORT_LINK_BYTES = 3
#: This is used to find existing short ids
SHORT_LINK_ID_UPPER_BOUND = 2 ** (SHORT_LINK_BYTES * 8)

#: Length limit for bigint. This is a constant and should not be revised
FULL_LINK_BYTES = 8

#: Length limit for Base64 rendering of bigint
MAX_NAME_LENGTH = 11

#: Base64 rendering of 8 null bytes, used to expand a short link to full bigint size
NAME_MASK = b'AAAAAAAAAAA='  # 11 bytes + 1 padding byte

#: Regex for requiring a name to have only URL-safe Base64 characters, used by
#: func:`name_to_bigint`. This deliberately allows zero length strings. The string ''
#: will map to id 0. The restriction on using id 0 is in :class:`Shortlink`.
_valid_name_re = re.compile('^[A-Za-z0-9_-]*$')


# MARK: Helpers ------------------------------------------------------------------------


def normalize_url(url: str | furl, default_scheme: str = 'https') -> furl:
    """Normalize a URL with a default scheme and path."""
    url = furl(url)
    if not url.scheme:
        url.scheme = default_scheme
    if not url.path:
        url.path = '/'
    return url


def random_bigint(smaller: bool = False) -> int:
    """
    Return a random signed bigint that is guaranteed to not be zero.

    :param bool smaller: Return a smaller number (with 24 bits instead of 64)
    """
    val = 0
    while val == 0:
        val = int.from_bytes(
            urandom(SHORT_LINK_BYTES if smaller else FULL_LINK_BYTES),
            'little',
            # Must use `signed=True` when full-size because PostgreSQL only supports
            # signed integers. However, smaller numbers must not be signed as negative
            # integers have the high bit set, and then they are no longer small bitwise
            signed=not smaller,  # signed=False if smaller
        )
    return val


def name_to_bigint(value: str | bytes) -> int:
    """
    Convert from a URL-safe Base64-encoded shortlink name to bigint.

    :raises ValueError: If the name doesn't map to a bigint
    :raises TypeError: If the name isn't of type `str` or `bytes`
    """
    if isinstance(value, str):
        bvalue = value.encode()
    elif isinstance(value, bytes):
        bvalue = value
        value = value.decode()
    else:
        raise TypeError(f"Unknown type for shortlink name: {value!r}")

    if len(bvalue) > MAX_NAME_LENGTH:
        raise ValueError(f"Shortlink name is too long: {value}")
    if _valid_name_re.search(value) is None:
        raise ValueError(f"Shortlink name contains invalid characters: {value}")

    # Pad value with mask
    bvalue = bvalue + NAME_MASK[len(bvalue) :]

    # Finally: cast Base64 to bigint. Must use `signed=True` because PostgreSQL only
    # supports signed integers. At this point the Base64 string is guaranteed to be
    # valid and exactly 8 bytes, so we don't need to validate further or handle
    # exceptions. Since Base64 is a 6-bit alphabet, 6 bits * 11 bytes = 66 bits, while
    # 8 bits * 8 bytes = 64 bits. The extra two bits are discarded when decoding Base64,
    # but have the side-effect of allowing multiple valid Base64 strings for the same
    # decoded value:
    #
    #     >>> urlsafe_b64decode(b'__________4=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xfe'
    #     >>> urlsafe_b64decode(b'__________5=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xfe'
    #     >>> urlsafe_b64decode(b'__________6=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xfe'
    #     >>> urlsafe_b64decode(b'__________7=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xfe'
    #
    #     >>> urlsafe_b64decode(b'__________8=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xff'
    #     >>> urlsafe_b64decode(b'__________9=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xff'
    #     >>> urlsafe_b64decode(b'__________-=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xff'
    #     >>> urlsafe_b64decode(b'___________=')
    #     b'\xff\xff\xff\xff\xff\xff\xff\xff'

    return int.from_bytes(urlsafe_b64decode(bvalue), 'little', signed=True)


def bigint_to_name(value: int) -> str:
    """Convert a bigint into URL-safe Base64, returning a compact representation."""
    # Must use `signed=True` because PostgreSQL only supports signed integers
    return (
        urlsafe_b64encode(value.to_bytes(8, 'little', signed=True))
        .rstrip(b'=')
        .rstrip(b'A')
        .decode()
    )


def url_blake2b160_hash(value: str | furl) -> bytes:
    """
    Hash a URL, for duplicate URL lookup.

    This function is currently not used as its utility is uncertain:

    1. Since hashes are shorter than full URLs, a URL lookup by hash may have better
       performance.
    2. However, indexing the URL itself will let us perform LIKE queries to find
       URLs matching paths or origins. Since an index is necessary for this, having
       another index for the hash may degrade overall INSERT performance.
    3. Hash index performance may be better if it uses 128 bits and is indexed as a UUID
       integer rather than a string/binary, but this is speculative and needs homework.
    """
    value = str(normalize_url(value))
    return hashlib.blake2b(value.encode('utf-8'), digest_size=20).digest()


class ShortLinkToBigIntComparator(Comparator):  # pylint: disable=abstract-method
    """
    Comparator to allow lookup by shortlink name instead of numeric id.

    If the provided name is invalid, :func:`name_to_bigint` will raise exceptions.
    """

    def __eq__(self, other: object) -> sa.ColumnElement[bool]:  # type: ignore[override]
        """Return an expression for column == other."""
        if isinstance(other, str | bytes):
            return self.__clause_element__() == name_to_bigint(other)  # type: ignore[return-value]
        return sa.sql.expression.false()

    is_ = __eq__  # type: ignore[assignment]

    def in_(  # type: ignore[override]
        self, other: Iterable[str | bytes]
    ) -> sa.ColumnElement:
        """Return an expression for other IN column."""
        return self.__clause_element__().in_(  # type: ignore[attr-defined]
            [name_to_bigint(v) for v in other]
        )


# MARK: Models -------------------------------------------------------------------------


class Shortlink(NoIdMixin, Model):
    """A short link to a full-size link, for use over SMS."""

    __tablename__ = 'shortlink'

    #: Non-persistent attribute for Shortlink.new to flag if this is a new shortlink.
    #: Any future instance cache system must NOT cache this value
    is_new = False

    # id of this shortlink, saved as a bigint (8 bytes)
    id: Mapped[int] = with_roles(
        # id cannot use the `immutable` wrapper because :meth:`new` changes the id when
        # handling collisions. This needs an "immutable after commit" handler
        sa_orm.mapped_column(
            sa.BigInteger, autoincrement=False, nullable=False, primary_key=True
        ),
        read={'all'},
    )
    #: URL target of this shortlink
    url: Mapped[furl] = with_roles(
        immutable(sa_orm.mapped_column(UrlType, nullable=False, index=True)),
        read={'all'},
    )
    #: Id of account that created this shortlink (optional)
    created_by_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('account.id', ondelete='SET NULL'), default=None, nullable=True
    )
    #: Account that created this shortlink (optional)
    created_by: Mapped[Account | None] = relationship()

    #: Is this link enabled? If not, render 410 Gone
    enabled: Mapped[bool] = sa_orm.mapped_column(default=True)

    @hybrid_property
    def name(self) -> str:
        """Return string representation of id, for use in short URLs."""
        if self.id is None:
            return ''  # type: ignore[unreachable]
        return bigint_to_name(self.id)

    @name.inplace.setter
    def _name_setter(self, value: str | bytes) -> None:
        """Set a name."""
        self.id = name_to_bigint(value)

    @name.inplace.comparator
    @classmethod
    def _name_comparator(cls) -> ShortLinkToBigIntComparator:
        """Compare name to id in a SQL expression."""
        return ShortLinkToBigIntComparator(cls.id)

    # MARK: Validators

    @sa_orm.validates('id')
    def _validate_id_not_zero(self, _key: str, value: int) -> int:
        if value == 0:
            raise ValueError("Id cannot be zero")
        return value

    @sa_orm.validates('url')
    def _validate_url(self, _key: str, value: str) -> str:
        # If URL hashes are added to the Shortlink model, the hash value must be set
        # here using `url_blake2b160_hash(value)`
        return str(normalize_url(value))

    # MARK: Methods

    def __repr__(self) -> str:
        """Return string representation of self."""
        return f'Shortlink(name={self.name!r}, url={self.url!r})'

    @overload
    @classmethod
    def new(
        cls,
        url: str | furl,
        *,
        name: str | None = None,
        shorter: bool = False,
        reuse: Literal[False] = False,
        actor: Account | None = None,
    ) -> Shortlink: ...

    @overload
    @classmethod
    def new(
        cls,
        url: str | furl,
        *,
        name: Literal[None] = None,
        shorter: bool = False,
        reuse: Literal[True] = True,
        actor: Account | None = None,
    ) -> Shortlink: ...

    @classmethod
    def new(
        cls,
        url: str | furl,
        *,
        name: str | None = None,
        shorter: bool = False,
        reuse: bool = False,
        actor: Account | None = None,
    ) -> Shortlink:
        """
        Create a new shortlink.

        This method MUST be used instead of the default constructor. It ensures the
        generated Shortlink instance has a unique id.
        """
        # This method is not named __new__ because SQLAlchemy depends on the default
        # implementation of __new__ when loading instances from the database.
        # https://docs.sqlalchemy.org/en/14/orm/constructors.html
        url = normalize_url(url)
        if reuse:
            if name:
                # The overload definitions are meant to ensure that mypy will flag any
                # code that uses both `reuse` and `name` parameters, but we'll check
                # for it anyway
                raise TypeError(
                    "Custom name cannot be provided when reusing an existing shortlink"
                )

            if shorter:
                existing = cls.query.filter(
                    Shortlink.url == url,
                    Shortlink.enabled.is_(True),
                    Shortlink.id > 0,
                    Shortlink.id < SHORT_LINK_ID_UPPER_BOUND,
                ).first()
            else:
                existing = cls.query.filter_by(url=url, enabled=True).first()
            if existing:
                return existing
        # First time we're seeing this URL? Process it.
        if name:
            # User wants a custom name? Try using it, but no guarantee this will work
            try:
                shortlink = cls(name=name, url=url, created_by=actor)
                shortlink.is_new = True
                # 1. Emit `BEGIN SAVEPOINT`
                savepoint = db.session.begin_nested()
                # 2. Tell SQLAlchemy to prepare to commit this record within savepoint
                db.session.add(shortlink)
                # 3. Emit `RELEASE SAVEPOINT`
                savepoint.commit()
            except IntegrityError as exc:
                # 4. Emit `ROLLBACK TO SAVEPOINT`
                savepoint.rollback()
                # Name not available. Re-raise as a ValueError
                raise ValueError(f"Shortlink name is not available: {name}") from exc
            return shortlink

        # Not a custom name. Keep trying ids until one succeeds
        shortlink = cls(id=random_bigint(shorter), url=url, created_by=actor)
        shortlink.is_new = True
        while True:
            if profanity.contains_profanity(shortlink.name):
                shortlink.id = random_bigint(shorter)
                continue
            try:
                savepoint = db.session.begin_nested()
                db.session.add(shortlink)
                savepoint.commit()
                break
            except IntegrityError:
                savepoint.rollback()
                shortlink.id = random_bigint(shorter)
        return shortlink

    @classmethod
    def name_available(cls, name: str) -> bool:
        """Check if a name is available to use for a new shortlink."""
        try:
            existing = db.session.query(
                cls.query.filter(cls.name == name)
                .options(sa_orm.load_only(cls.id))
                .exists()
            ).scalar()
            return not existing
        except (ValueError, TypeError):
            # Name is not valid (`name_to_bigint` raised error)
            return False

    @classmethod
    def get(cls, name: str | bytes, ignore_enabled: bool = False) -> Shortlink | None:
        """
        Get a shortlink by name, if existing and not disabled.

        :param bool ignore_enabled: Don't check if existing shortlink is enabled
        """
        try:
            idv = name_to_bigint(name)
        except (ValueError, TypeError):
            return None
        obj = db.session.get(
            cls, idv, options=[sa_orm.load_only(cls.id, cls.url, cls.enabled)]
        )
        if obj is not None and (ignore_enabled or obj.enabled):
            return obj
        return None
