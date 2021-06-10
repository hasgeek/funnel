"""Shortlink models."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from os import urandom
from typing import Optional, Union, overload
import binascii
import hashlib

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import Comparator

from furl import furl
from typing_extensions import Literal
from url_normalize import url_normalize

from coaster.sqlalchemy import immutable, with_roles

from . import NoIdMixin, UrlType, db, hybrid_property
from .user import User

# --- Constants ------------------------------------------------------------------------

#: Size for for SMS and other length-sensitive uses. This can be raised from 3 to 4
#: bytes as usage grows
SHORT_LINK_BYTES = 3

#: Length limit for bigint. This is a constant and should not be revised
FULL_LINK_BYTES = 8

#: Length limit for Base64 rendering of bigint
MAX_NAME_LENGTH = 11

#: Base64 rendering of 8 null bytes, used to expand a short link to full bigint size
NAME_MASK = b'AAAAAAAAAAA='


# --- Helpers --------------------------------------------------------------------------


def shortlink_to_bigint(value: Union[int, bytes, str]) -> int:
    """Convert from a Base64-encoded shortlink name to bigint."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        bvalue = value.encode()
    elif isinstance(value, bytes):
        bvalue = value
        value = value.decode()
    else:  # type: ignore[unreachable]
        raise TypeError(f"Unknown type for shortlink name: {value!r}")

    if len(bvalue) > MAX_NAME_LENGTH:
        raise ValueError(f"Shortlink name is too long: {value}")
    bvalue = bvalue + NAME_MASK[len(bvalue) :]  # Pad value with mask
    try:
        # Cast Base64 to bigint. Must use `signed=True` because PostgreSQL only
        # supports signed integers
        return int.from_bytes(urlsafe_b64decode(bvalue), 'little', signed=True)
    except binascii.Error:
        raise ValueError(
            f"Shortlink name isn't valid Base64: {value} -> {bvalue.decode()}"
        )


def bigint_to_shortlink(value: int) -> str:
    """Convert a bigint into Base64, returning the shortest possible representation."""
    # Must use `signed=True` because PostgreSQL only supports signed integers
    return (
        urlsafe_b64encode(value.to_bytes(8, 'little', signed=True))
        .rstrip(b'=')
        .rstrip(b'A')
        .decode()
    )


def url_blake2b_hash(value: Union[str, furl], normalize=True) -> bytes:
    """Hash a URL, for duplicate URL lookup."""
    if normalize:
        value = url_normalize(str(value))
    else:
        value = str(value)
    return hashlib.blake2b(value.encode('utf-8')).digest()


def random_bigint(smaller: bool = False) -> int:
    """
    Return a random signed bigint that is guaranteed to not be zero.

    :param bool shorter: Return a smaller number (currently 24 bits instead of 64)
    """
    val = 0
    while val == 0:
        val = int.from_bytes(
            urandom(SHORT_LINK_BYTES if smaller else FULL_LINK_BYTES),
            'little',
            signed=True,
        )
    return val


class ShortLinkToBigIntComparator(Comparator):
    """Comparator to allow lookup by shortlink name instead of numeric id."""

    def __eq__(self, value):
        """Return an expression for column == value."""
        try:
            value = shortlink_to_bigint(value)
        except (ValueError, TypeError):
            return False
        return self.__clause_element__() == value

    def __ne__(self, value):
        """Return an expression for column != value."""
        try:
            value = shortlink_to_bigint(value)
        except (ValueError, TypeError):
            return True
        return self.__clause_element__() != value

    def in_(self, value):
        """Return an expression for value IN column."""

        def errordecode(val):
            try:
                return shortlink_to_bigint(val)
            except (ValueError, TypeError):
                return None

        valuelist = (v for v in (errordecode(val) for val in value) if v is not None)
        return self.__clause_element__().in_(valuelist)


# --- Models ---------------------------------------------------------------------------


class Shortlink(NoIdMixin, db.Model):
    __tablename__ = 'shortlink'

    # id of this shortlink, saved as a bigint (8 bytes)
    id = with_roles(  # NOQA: A003
        immutable(
            db.Column(
                db.BigInteger, autoincrement=False, nullable=False, primary_key=True
            )
        ),
        read={'all'},
    )
    #: URL target of this shortlink
    url = with_roles(immutable(db.Column(UrlType, nullable=False)), read={'all'})
    #: Blake2b hash of URL (PostgreSQL BYTEA)
    blake2b = immutable(db.Column(db.LargeBinary, nullable=False, index=True))
    #: Id of user who created this shortlink (optional)
    user_id = db.Column(
        None, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    #: User who created this shortlink (optional)
    user = db.relationship(User)

    #: Is this link enabled? If not, render 410 Gone
    enabled = db.Column(db.Boolean, nullable=False, default=True)

    @hybrid_property
    def name(self) -> str:
        """Return string representation of id, for use in short URLs."""
        if self.id is None:
            return ''
        return bigint_to_shortlink(self.id)

    @name.setter
    def name(self, value: Union[str, bytes]):
        self.id = shortlink_to_bigint(value)

    @name.comparator
    def name(cls):  # NOQA: N805
        return ShortLinkToBigIntComparator(cls.id)

    # --- Validators

    @db.validates('id')
    def _validate_id_not_zero(self, key, value: int) -> int:
        if value == 0:
            raise ValueError("Id cannot be zero")
        return value

    @db.validates('url')
    def _validate_url(self, key, value) -> str:
        value = url_normalize(str(value))
        self.blake2b = url_blake2b_hash(value, normalize=False)
        return value

    # --- Constructor

    @overload
    @classmethod
    def new(
        cls,
        url: Union[str, furl],
        *,
        name: str = None,
        shorter: bool = False,
        reuse: Literal[False] = False,
        actor: Optional[User] = None,
    ) -> Shortlink:
        ...

    @overload
    @classmethod
    def new(
        cls,
        url: Union[str, furl],
        *,
        name: Literal[None] = None,
        shorter: bool = False,
        reuse: Literal[True] = True,
        actor: Optional[User] = None,
    ) -> Shortlink:
        ...

    @classmethod
    def new(
        cls,
        url: Union[str, furl],
        *,
        name: Optional[str] = None,
        shorter: bool = False,
        reuse: bool = False,
        actor: Optional[User] = None,
    ) -> Shortlink:
        """
        Create a new shortlink.

        This method MUST be used instead of the default constructor. It ensures the
        generated Shortlink instance has a unique id.
        """
        if reuse:
            if name:
                raise TypeError(
                    "Custom name cannot be provided when reusing an existing shortlink"
                )
            existing = cls.query.filter_by(
                blake2b=url_blake2b_hash(url), enabled=True
            ).first()
            if existing:
                return existing
        # First time we're seeing this URL? Process it.
        if name:
            # User wants a custom name? Try using it, but no guarantee this will work
            try:
                shortlink = cls(name=name, url=url, actor=actor)
                # 1. Emit `BEGIN SAVEPOINT`
                savepoint = db.session.begin_nested()
                # 2. Tell SQLAlchemy to prepare to commit this record within savepoint
                db.session.add(shortlink)
                # 3. Emit `RELEASE SAVEPOINT`
                savepoint.commit()
            except IntegrityError:
                # 4. Emit `ROLLBACK TO SAVEPOINT`
                savepoint.rollback()
                # Name not available. Re-raise as a ValueError
                raise ValueError(f"Shortlink name is not available: {name}")
            return shortlink

        # Not a custom name. Keep trying ids until one succeeds
        shortlink = cls(id=random_bigint(shorter), url=url, actor=actor)
        while True:
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
    def name_available(cls, name: str):
        """Check if a name is available to use for a new shortlink."""
        try:
            existing = db.session.query(
                cls.query.filter(cls.name == name)
                .options(db.load_only(cls.id))
                .exists()
            ).scalar()
            return not existing
        except ValueError:
            # Name is not valid (`cls.name` comparator raised ValueError)
            return False
