"""Base class for history-preserving membership records."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime as datetime_type
from enum import ReprEnum
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Protocol, Self, TypeVar
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.sql.expression import ColumnElement
from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import StateManager, immutable, with_roles

from .account import Account
from .base import (
    BaseMixin,
    Mapped,
    UuidMixin,
    db,
    declarative_mixin,
    declared_attr,
    hybrid_property,
    relationship,
    sa,
    sa_orm,
)
from .helpers import IntTitle
from .reorder_mixin import ReorderMixin

# Export only symbols needed in views.
__all__ = [
    'MembershipRecordTypeEnum',
    'MembershipError',
    'MembershipRevokedError',
    'MembershipRecordTypeError',
]

# MARK: Typing -------------------------------------------------------------------------

MembershipType = TypeVar('MembershipType', bound='ImmutableMembershipMixin')


class MembershipMixinProtocol(Protocol):
    member_id: Mapped[int]
    member: declared_attr[Account]
    _local_data_only: bool
    parent_id_column: ClassVar[str]

    def replace(self, actor: Account, **data: Any) -> Self: ...


class FrozenAttributionSubclassProtocol(MembershipMixinProtocol, Protocol):
    _title: declared_attr[str | None]


class ReorderSubclassProtocol(Protocol):
    seq: Mapped[Any]
    parent_id: Mapped[Any]
    parent: Mapped[Any]
    is_active: hybrid_property[bool]

    @property
    def parent_scoped_reorder_query_filter(
        self: ReorderSubclassProtocol,
    ) -> ColumnElement[bool]: ...


MembershipMixinType = TypeVar('MembershipMixinType', bound=MembershipMixinProtocol)
FrozenAttributionType = TypeVar(
    'FrozenAttributionType', bound=FrozenAttributionSubclassProtocol
)


# MARK: Enum ---------------------------------------------------------------------------


class MembershipRecordTypeEnum(IntTitle, ReprEnum):
    """Membership record types."""

    #: An invite represents a potential future membership, but not a current membership
    INVITE = 1, __("Invite")
    #: An accept recognises a conversion from an invite into a current membership
    ACCEPT = 2, __("Accept")
    #: A direct add recognises a current membership without proof of consent
    DIRECT_ADD = 3, __("Direct add")
    #: An amendment is when data in the record has been changed
    AMEND = 4, __("Amend")
    #: A migrate record says this used to be some other form of membership and has been
    #: created due to a technical change in the product
    # Forthcoming: MIGRATE = 5, __("Migrate")


# MARK: Exceptions ---------------------------------------------------------------------


class MembershipError(Exception):
    """Base class for membership errors."""


class MembershipRevokedError(MembershipError):
    """Membership record has already been revoked."""


class MembershipRecordTypeError(MembershipError):
    """Membership record type is invalid."""


# MARK: Classes ------------------------------------------------------------------------


@declarative_mixin
class ImmutableMembershipMixin(UuidMixin, BaseMixin[UUID, Account]):
    """Support class for immutable memberships."""

    if TYPE_CHECKING:
        #: Subclass has a table name
        __tablename__: str
        #: Parent column (declare as synonym of 'profile_id' or 'project_id' in
        #: subclasses)
        parent_id: Mapped[Any] | None
        #: Parent object
        parent: Mapped[Any] | None

    #: Can granted_by be null? Only in memberships based on legacy data
    __null_granted_by__: ClassVar[bool] = False
    #: List of columns that will be copied into a new row when a membership is amended
    __data_columns__: ClassVar[Iterable[str]] = ()
    #: Name of the parent id column, used in SQL constraints
    parent_id_column: ClassVar[str]
    #: Foreign key column to account table
    member_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        default=None,
        nullable=False,
        index=True,
    )

    @classmethod
    def __member(cls) -> Mapped[Account]:
        """Member in this membership record."""
        return relationship(Account, foreign_keys=[cls.member_id])

    member = with_roles(
        declared_attr(__member),
        read={'member', 'editor'},
        grants_via={None: {'admin': 'member'}},
    )
    del __member

    @declared_attr
    @classmethod
    def user(cls) -> Mapped[Account]:
        """Legacy alias for member in this membership record."""
        return sa_orm.synonym('member')

    __table_args__: tuple  # pyright: ignore[reportRedeclaration]

    @declared_attr.directive  # type: ignore[no-redef]
    @classmethod
    def __table_args__(cls) -> tuple:
        """Table arguments for SQLAlchemy."""
        try:
            args = list(super().__table_args__)  # type: ignore[misc]
        except AttributeError:
            args = []
        kwargs = args.pop(-1) if args and isinstance(args[-1], dict) else None
        if cls.parent_id_column:
            args.append(
                sa.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    cls.parent_id_column,
                    'member_id',
                    unique=True,
                    postgresql_where='revoked_at IS NULL',
                ),
            )
        else:
            args.append(
                sa.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    'member_id',
                    unique=True,
                    postgresql_where='revoked_at IS NULL',
                ),
            )
        if kwargs:
            args.append(kwargs)
        return tuple(args)

    #: Should an active membership record be revoked when the member is soft-deleted?
    #: (Hard deletes will cascade and also delete all membership records.)
    revoke_on_member_delete: ClassVar[bool] = True

    #: Internal flag for using only local data when replacing a record, used from
    #: :class:`FrozenAttributionMixin`
    _local_data_only: bool = False

    #: Start time of membership, ordinarily a mirror of created_at except
    #: for records created when the member table was added to the database
    granted_at: Mapped[datetime_type] = with_roles(
        immutable(
            sa_orm.mapped_column(
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                insert_default=sa.func.utcnow(),
                default=None,
            )
        ),
        read={'member', 'editor'},
    )
    #: End time of membership, ordinarily a mirror of updated_at
    revoked_at: Mapped[datetime_type | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True),
        read={'member', 'editor'},
    )
    #: Record type
    record_type: Mapped[int] = with_roles(
        immutable(
            sa_orm.mapped_column(
                StateManager.check_constraint(
                    'record_type', MembershipRecordTypeEnum, sa.Integer
                ),
                default=MembershipRecordTypeEnum.DIRECT_ADD,
                nullable=False,
            )
        ),
        read={'member', 'editor'},
    )

    @cached_property
    def record_type_enum(self) -> MembershipRecordTypeEnum:
        return MembershipRecordTypeEnum(self.record_type)

    with_roles(record_type_enum, read={'member', 'editor'})

    @declared_attr
    @classmethod
    def revoked_by_id(cls) -> Mapped[int | None]:
        """Id of user who revoked the membership."""
        return sa_orm.mapped_column(
            sa.ForeignKey('account.id', ondelete='SET NULL'),
            default=None,
            nullable=True,
        )

    @with_roles(read={'member', 'editor'}, grants={'editor'})
    @declared_attr
    @classmethod
    def revoked_by(cls) -> Mapped[Account | None]:
        """User who revoked the membership."""
        return relationship(Account, foreign_keys=[cls.revoked_by_id])

    @declared_attr
    @classmethod
    def granted_by_id(cls) -> Mapped[int | None]:
        """
        Id of user who assigned the membership.

        This is nullable only for historical data. New records always require a value
        for granted_by.
        """
        return sa_orm.mapped_column(
            sa.ForeignKey('account.id', ondelete='SET NULL'),
            default=None,
            nullable=cls.__null_granted_by__,
        )

    @with_roles(read={'member', 'editor'}, grants={'editor'})
    @declared_attr
    @classmethod
    def granted_by(cls) -> Mapped[Account | None]:
        """User who assigned the membership."""
        return relationship(Account, foreign_keys=[cls.granted_by_id])

    @hybrid_property
    def is_active(self) -> bool:
        """Test if membership record is active (not revoked, not an invite)."""
        return (
            self.revoked_at is None
            and self.record_type != MembershipRecordTypeEnum.INVITE
        )

    @is_active.inplace.expression
    @classmethod
    def _is_active_expression(cls) -> sa.ColumnElement[bool]:
        """Test if membership record is active as a SQL expression."""
        return sa.and_(
            cls.revoked_at.is_(None), cls.record_type != MembershipRecordTypeEnum.INVITE
        )

    with_roles(is_active, read={'member'})

    @hybrid_property
    def is_invite(self) -> bool:
        """Test if membership record is an invitation."""
        return self.record_type == MembershipRecordTypeEnum.INVITE

    with_roles(is_invite, read={'member', 'editor'})

    @hybrid_property
    def is_amendment(self) -> bool:
        """Test if membership record is an amendment."""
        return self.record_type == MembershipRecordTypeEnum.AMEND

    with_roles(is_amendment, read={'member', 'editor'})

    def __repr__(self) -> str:
        # pylint: disable=using-constant-test
        return (
            f'<{self.__class__.__name__} {self.member!r} in {self.parent!r} '
            + ('active' if self.is_active else 'revoked')
            + '>'
        )

    @cached_property
    def offered_roles(self) -> set[str]:
        """Return roles offered by this membership record."""
        return set()

    # Subclasses must gate these methods in __roles__

    @with_roles(call={'member', 'editor'})
    def revoke(self, actor: Account) -> None:
        """Revoke this membership record."""
        if self.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        self.revoked_at = sa.func.utcnow()
        self.revoked_by = actor

    @with_roles(call={'editor'})
    def replace(self, actor: Account, _accept: bool = False, **data: Any) -> Self:
        """Replace this membership record with changes to role columns."""
        if self.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        if not set(data.keys()).issubset(self.__data_columns__):
            raise AttributeError("Unknown data attribute")

        # Perform sanity check. If nothing changed, just return self
        has_changes = False
        if self.record_type == MembershipRecordTypeEnum.INVITE and _accept:
            # If the existing record is an INVITE and this is an ACCEPT, we have
            # a record change even if no data changed
            has_changes = True
        else:
            # If it's not an ACCEPT, are the supplied data different from existing?
            self._local_data_only = True
            for column_name, column_value in data.items():
                if column_value != getattr(self, column_name):
                    has_changes = True
            del self._local_data_only
        if not has_changes:
            # Nothing is changing. This is probably a form submit with no changes.
            # Do nothing and return self
            return self

        # An actual change? Revoke this record and make a new record

        self.revoked_at = sa.func.utcnow()
        self.revoked_by = actor
        self._local_data_only = True
        new = self.copy_template(parent_id=self.parent_id, granted_by=actor)
        del self._local_data_only

        # if existing record type is INVITE, then ACCEPT or amend as new INVITE
        # else replace it with AMEND
        if self.record_type == MembershipRecordTypeEnum.INVITE:
            if _accept:
                new.record_type = MembershipRecordTypeEnum.ACCEPT
            else:
                new.record_type = MembershipRecordTypeEnum.INVITE
        else:
            new.record_type = MembershipRecordTypeEnum.AMEND

        self._local_data_only = True
        for column in self.__data_columns__:
            if column in data:
                setattr(new, column, data[column])
            else:
                setattr(new, column, getattr(self, column))
        del self._local_data_only
        db.session.add(new)
        return new

    @with_roles(call={'editor'})
    def amend_by(self, actor: Account) -> AmendMembership[Self]:
        """Amend a membership in a `with` context."""
        return AmendMembership(self, actor)

    def merge_and_replace(self, actor: Account, other: Self) -> Self:
        """Replace this record by merging data from an independent record."""
        if self.__class__ is not other.__class__:
            raise TypeError("Merger requires membership records of the same type")
        if self.revoked_at is not None:
            raise MembershipRevokedError("This membership record has been revoked")
        if other.revoked_at is not None:
            raise MembershipRevokedError("Can't merge with a revoked membership record")

        if (
            self.record_type == MembershipRecordTypeEnum.INVITE
            and other.record_type != MembershipRecordTypeEnum.INVITE
        ):
            # If we are an INVITE but the other is not an INVITE, then we must ACCEPT
            # the INVITE before proceeding to an AMEND merger
            this = self.accept(actor)
        else:
            # If both records are invites or neither is an invite, use existing records
            this = self

        self._local_data_only = True
        data_columns = {}
        for column in this.__data_columns__:
            column_value = getattr(this, column)
            if not column_value:
                # Replace falsy values with value from the other record. This may need
                # a more robust mechanism in the future if there are multi-value columns
                column_value = getattr(other, column)
            data_columns[column] = column_value
        del self._local_data_only
        replacement = this.replace(actor, **data_columns)
        other.revoke(actor)

        return replacement

    @with_roles(call={'member'})
    def accept(self, actor: Account) -> Self:
        """Accept a membership invitation."""
        if self.record_type != MembershipRecordTypeEnum.INVITE:
            raise MembershipRecordTypeError("This membership record is not an invite")
        if 'member' not in self.roles_for(actor):
            raise ValueError("Invite must be accepted by the invited user")
        return self.replace(actor, _accept=True)

    @hybrid_property
    def is_self_granted(self) -> bool:
        """Return True if the member in this record is also the granting actor."""
        return self.member_id == self.granted_by_id or (
            self.granted_by is not None and 'member' in self.roles_for(self.granted_by)
        )

    with_roles(is_self_granted, read={'member', 'editor'})

    @hybrid_property
    def is_self_revoked(self) -> bool:
        """Return True if the member in this record is also the revoking actor."""
        return self.member_id == self.revoked_by_id or (
            self.revoked_by is not None and 'member' in self.roles_for(self.revoked_by)
        )

    with_roles(is_self_revoked, read={'member', 'editor'})

    def copy_template(self, **kwargs: Any) -> Self:
        """Make a copy of self for customization."""
        return self.__class__(member=self.member, **kwargs)  # type: ignore[call-arg]

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """
        Migrate membership records from one account to another.

        If both accounts have active records, they are merged into a new record in the
        new account's favour. All revoked records for the old account are transferred to
        the new account.
        """
        # Look up all active membership records of the subclass's type for the old user
        # account. `cls` here represents the subclass.
        old_account_records = cls.query.filter(
            cls.member == old_account, cls.revoked_at.is_(None)
        ).all()
        # Look up all conflicting memberships for the new account. Limit lookups by
        # parent except when the membership type doesn't have a parent (SiteMembership).
        if cls.parent_id is not None:
            new_account_records = cls.query.filter(
                cls.member == new_account,
                cls.revoked_at.is_(None),
                cls.parent_id.in_([r.parent_id for r in old_account_records]),
            ).all()
        else:
            new_account_records = cls.query.filter(
                cls.member == new_account,
                cls.revoked_at.is_(None),
            ).all()
        new_account_records_by_parent = {r.parent_id: r for r in new_account_records}

        for record in old_account_records:
            if record.parent_id in new_account_records_by_parent:
                # Where there is a conflict, merge the records
                new_account_records_by_parent[record.parent_id].merge_and_replace(
                    new_account, record
                )
                db.session.flush()

        # Transfer all revoked records and non-conflicting active records. At this point
        # no filter is necessary as the conflicting records have all been merged.
        cls.query.filter(cls.member == old_account).update(
            {'member_id': new_account.id}, synchronize_session=False
        )
        # Also update the revoked_by and granted_by accounts
        cls.query.filter(cls.revoked_by == old_account).update(
            {'revoked_by_id': new_account.id}, synchronize_session=False
        )
        cls.query.filter(cls.granted_by == old_account).update(
            {'granted_by_id': new_account.id}, synchronize_session=False
        )
        db.session.flush()


@declarative_mixin
class ReorderMembershipMixin(ImmutableMembershipMixin, ReorderMixin):
    """Customizes ReorderMixin for membership models."""

    #: Sequence number. Not immutable, and may be overwritten by ReorderMixin as a
    #: side-effect of reordering other records. This is not considered a revision.
    #: However, it can be argued that relocating a sponsor in the list constitutes a
    #: change that must be recorded as a revision. We may need to change our opinion
    #: on `seq` being mutable in a future iteration.
    seq: Mapped[int] = sa_orm.mapped_column(nullable=False)

    __table_args__: tuple  # pyright: ignore[reportRedeclaration]

    @declared_attr.directive  # type: ignore[no-redef]
    @classmethod
    def __table_args__(cls) -> tuple:  # type: ignore[override]
        """Table arguments."""
        try:
            args = list(super().__table_args__)
        except AttributeError:
            args = []
        kwargs = args.pop(-1) if args and isinstance(args[-1], dict) else None
        # Add unique constraint on :attr:`seq` for active records
        args.append(
            sa.Index(
                'ix_' + cls.__tablename__ + '_seq',
                cls.parent_id_column,
                'seq',
                unique=True,
                postgresql_where='revoked_at IS NULL',
            ),
        )
        if kwargs:
            args.append(kwargs)
        return tuple(args)

    def __init__(self: ReorderSubclassProtocol, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Assign a default value to `seq`
        if self.seq is None:  # Will be None until first commit
            self.seq = (
                sa.select(sa.func.coalesce(sa.func.max(self.__class__.seq) + 1, 1))
                .where(self.parent_scoped_reorder_query_filter)
                .scalar_subquery()
            )

    @property
    def parent_scoped_reorder_query_filter(
        self: ReorderSubclassProtocol,
    ) -> ColumnElement[bool]:
        """
        Return a query filter that includes a scope limitation to active records.

        Used by:
        * :meth:`__init__` to assign an initial sequence number, and
        * :class:`ReorderMixin` to reassign sequence numbers
        """
        cls = self.__class__
        # During __init__, if the constructor only received `parent`, it doesn't yet
        # know `parent_id`. Therefore we have to be prepared for two possible returns
        if self.parent_id is not None:
            return sa.and_(
                cls.parent_id == self.parent_id,
                cls.is_active,
            )
        return sa.and_(
            cls.parent == self.parent,
            cls.is_active,
        )


@declarative_mixin
class FrozenAttributionMixin:
    """Provides a `title` data column and support method to freeze it."""

    @classmethod
    def __title(cls) -> Mapped[str | None]:
        """Create optional attribution title for this membership record."""
        return immutable(
            sa_orm.mapped_column(
                'title', sa.Unicode, sa.CheckConstraint("title <> ''"), nullable=True
            )
        )

    _title = declared_attr(__title)
    del __title

    @property
    def title(self: FrozenAttributionSubclassProtocol) -> str:
        """Attribution title for this record."""
        if self._local_data_only:
            # self._title may be None when returning local data
            return self._title  # type: ignore[return-value]
        return self._title or self.member.title

    @title.setter
    def title(self, value: str | None) -> None:
        """Set or clear custom attribution title."""
        # The title column is marked immutable, so this setter can only be called once,
        # typically during __init__
        self._title = value or None  # Don't set empty string

    @property
    def pickername(self: FrozenAttributionSubclassProtocol) -> str:
        """Return member's pickername, but only if attribution isn't frozen."""
        return self._title if self._title else self.member.pickername

    @with_roles(call={'owner', 'member'})
    def freeze_member_attribution(
        self: FrozenAttributionType, actor: Account
    ) -> FrozenAttributionType:
        """Freeze member attribution and return a replacement record."""
        if self._title is None:
            membership = self.replace(actor=actor, title=self.member.title)
        else:
            membership = self
        return membership


class AmendMembership(Generic[MembershipType]):
    """
    Helper class for editing a membership record from a form.

    Usage via the membership base class::

        with membership.amend_by(actor) as amendment:
            amendment.attr = value
            form.populate_obj(amendment)

        new_membership = amendment.membership

    The amendment object is not a membership record but a proxy that allows writing
    to any attribute listed as a data column.
    """

    membership: MembershipType
    _actor: Account
    _new: dict[str, Any]

    def __init__(self, membership: MembershipType, actor: Account) -> None:
        """Create an amendment placeholder."""
        if membership.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        object.__setattr__(self, 'membership', membership)
        object.__setattr__(self, '_actor', actor)
        object.__setattr__(self, '_new', {})

    def __getattr__(self, attr: str) -> Any:
        """Get an attribute from the underlying record."""
        if attr in self._new:
            return self._new[attr]
        return getattr(self.membership, attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        """Set an amended value."""
        if attr not in self.membership.__data_columns__:
            raise AttributeError(
                f"{attr} cannot be set",
                name=attr,
                obj=SimpleNamespace(
                    **{_: None for _ in self.membership.__data_columns__}
                ),
            )
        self._new[attr] = value

    def __enter__(self) -> AmendMembership:
        """Enter a `with` context."""
        return self

    def __exit__(self, exc_type: Any, _exc_value: Any, _traceback: Any) -> None:
        """Exit a `with` context and replace the membership record."""
        if exc_type is None:
            object.__setattr__(
                self, 'membership', self.membership.replace(self._actor, **self._new)
            )

    def commit(self) -> MembershipType:
        """Commit and return a replacement record when not using a `with` context."""
        self.__exit__(None, None, None)
        return self.membership


@event.listens_for(Account, 'mapper_configured', propagate=True)
def _confirm_enumerated_mixins(_mapper: Any, cls: type[Account]) -> None:
    """Confirm that the membership collection attributes actually exist."""
    expected_class = ImmutableMembershipMixin
    if issubclass(cls, Account):
        expected_class = ImmutableMembershipMixin
    for source in (
        cls.__active_membership_attrs__,
        cls.__noninvite_membership_attrs__,
    ):
        for attr_name in source:
            attr_relationship = getattr(cls, attr_name, None)
            if attr_relationship is None:
                raise AttributeError(
                    f'{cls.__name__} does not have a relationship named'
                    f' {attr_name!r} targeting a subclass of {expected_class.__name__}',
                    name=attr_name,
                    obj=cls,
                )
            if not issubclass(attr_relationship.property.mapper.class_, expected_class):
                raise AttributeError(
                    f'{cls.__name__}.{attr_name} should be a relationship to a'
                    f' subclass of {expected_class.__name__}',
                    name=attr_name,
                    obj=cls,
                )
