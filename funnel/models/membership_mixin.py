"""Base class for history-preserving membership records."""

from __future__ import annotations

from datetime import datetime as datetime_type
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Iterable,
    Optional,
    Set,
    TypeVar,
    Union,
)

from sqlalchemy import event
from sqlalchemy.sql.expression import ColumnElement

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import StateManager, immutable, with_roles
from coaster.utils import LabeledEnum

from ..typing import Mapped, OptionalMigratedTables
from . import (
    BaseMixin,
    UuidMixin,
    db,
    declarative_mixin,
    declared_attr,
    hybrid_property,
    sa,
)
from .profile import Profile
from .reorder_mixin import ReorderMixin
from .user import EnumerateMembershipsMixin, User

# Export only symbols needed in views.
__all__ = [
    'MEMBERSHIP_RECORD_TYPE',
    'MembershipError',
    'MembershipRevokedError',
    'MembershipRecordTypeError',
]

# --- Typing ---------------------------------------------------------------------------

MembershipType = TypeVar('MembershipType', bound='ImmutableMembershipMixin')
FrozenAttributionType = TypeVar('FrozenAttributionType', bound='FrozenAttributionMixin')
SubjectType = Union[Mapped[User], Mapped[Profile]]

# --- Enum -----------------------------------------------------------------------------


class MEMBERSHIP_RECORD_TYPE(LabeledEnum):  # noqa: N801
    """Membership record types."""

    # TODO: Convert into IntEnum

    INVITE = (1, 'invite', __("Invite"))
    ACCEPT = (2, 'accept', __("Accept"))
    DIRECT_ADD = (3, 'direct_add', __("Direct add"))
    AMEND = (4, 'amend', __("Amend"))
    # Forthcoming: MIGRATE = (5, 'migrate', __("Migrate"))


# --- Exceptions -----------------------------------------------------------------------


class MembershipError(Exception):
    """Base class for membership errors."""


class MembershipRevokedError(MembershipError):
    """Membership record has already been revoked."""


class MembershipRecordTypeError(MembershipError):
    """Membership record type is invalid."""


# --- Classes --------------------------------------------------------------------------


@declarative_mixin
class ImmutableMembershipMixin(UuidMixin, BaseMixin):
    """Support class for immutable memberships."""

    __uuid_primary_key__ = True
    #: Can granted_by be null? Only in memberships based on legacy data
    __null_granted_by__ = False
    #: List of columns that will be copied into a new row when a membership is amended
    __data_columns__: ClassVar[Iterable[str]] = ()
    #: Parent column (declare as synonym of 'profile_id' or 'project_id' in subclasses)
    parent_id: Optional[Mapped[int]]
    #: Parent object
    parent: Optional[Mapped[db.Model]]
    #: Subject of this membership (subclasses must define)
    subject: SubjectType

    #: Should an active membership record be revoked when the subject is soft-deleted?
    #: (Hard deletes will cascade and also delete all membership records.)
    revoke_on_subject_delete: ClassVar[bool] = True

    #: Internal flag for using only local data when replacing a record, used from
    #: :class:`FrozenAttributionMixin`
    _local_data_only: bool = False

    #: Start time of membership, ordinarily a mirror of created_at except
    #: for records created when the member table was added to the database
    granted_at: sa.Column[datetime_type] = immutable(
        with_roles(
            sa.Column(
                sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
            ),
            read={'subject', 'editor'},
        )
    )
    #: End time of membership, ordinarily a mirror of updated_at
    revoked_at: sa.Column[Optional[datetime_type]] = with_roles(
        sa.Column(sa.TIMESTAMP(timezone=True), nullable=True),
        read={'subject', 'editor'},
    )
    #: Record type
    record_type: sa.Column = immutable(
        with_roles(
            sa.Column(
                sa.Integer,
                StateManager.check_constraint('record_type', MEMBERSHIP_RECORD_TYPE),
                default=MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                nullable=False,
            ),
            read={'subject', 'editor'},
        )
    )

    @declared_attr
    def revoked_by_id(  # pylint: disable=no-self-argument
        cls,
    ) -> sa.Column[Optional[int]]:
        """Id of user who revoked the membership."""
        return db.Column(
            None, sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
        )

    @with_roles(read={'subject', 'editor'}, grants={'editor'})
    @declared_attr
    def revoked_by(  # pylint: disable=no-self-argument
        cls,
    ) -> Mapped[Optional[User]]:
        """User who revoked the membership."""
        return sa.orm.relationship(User, foreign_keys=[cls.revoked_by_id])

    @declared_attr
    def granted_by_id(cls) -> sa.Column[int]:  # pylint: disable=no-self-argument
        """
        Id of user who assigned the membership.

        This is nullable only for historical data. New records always require a value
        for granted_by.
        """
        return db.Column(
            None,
            sa.ForeignKey('user.id', ondelete='SET NULL'),
            nullable=cls.__null_granted_by__,
        )

    @with_roles(read={'subject', 'editor'}, grants={'editor'})
    @declared_attr
    def granted_by(  # pylint: disable=no-self-argument
        cls,
    ) -> Mapped[Optional[User]]:
        """User who assigned the membership."""
        return sa.orm.relationship(User, foreign_keys=[cls.granted_by_id])

    @hybrid_property
    def is_active(self) -> bool:
        """Test if membership record is active (not revoked, not an invite)."""
        return (
            self.revoked_at is None
            and self.record_type != MEMBERSHIP_RECORD_TYPE.INVITE
        )

    @is_active.expression
    def is_active(cls):  # noqa: N805  # pylint: disable=no-self-argument
        """Test if membership record is active as a SQL expression."""
        return sa.and_(
            cls.revoked_at.is_(None), cls.record_type != MEMBERSHIP_RECORD_TYPE.INVITE
        )

    with_roles(is_active, read={'subject'})

    @hybrid_property
    def is_invite(self) -> bool:
        """Test if membership record is an invitation."""
        return self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE

    with_roles(is_invite, read={'subject', 'editor'})

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} {self.subject!r} in {self.parent!r} '
            + ('active' if self.is_active else 'revoked')
            + '>'
        )

    @cached_property
    def offered_roles(self) -> Set[str]:
        """Return roles offered by this membership record."""
        return set()

    # Subclasses must gate these methods in __roles__

    @with_roles(call={'subject', 'editor'})
    def revoke(self, actor: User) -> None:
        """Revoke this membership record."""
        if self.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        self.revoked_at = sa.func.utcnow()
        self.revoked_by = actor

    def copy_template(self: MembershipType, **kwargs) -> MembershipType:
        """Make a copy of self for customization."""
        raise NotImplementedError("Subclasses must implement copy_template")

    @with_roles(call={'editor'})
    def replace(
        self: MembershipType, actor: User, accept: bool = False, **data: Any
    ) -> MembershipType:
        """Replace this membership record with changes to role columns."""
        if self.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        if not set(data.keys()).issubset(self.__data_columns__):
            raise AttributeError("Unknown data attribute")

        # Perform sanity check. If nothing changed, just return self
        has_changes = False
        if self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE and accept:
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
        new = self.copy_template(parent_id=self.parent_id, granted_by=self.granted_by)
        del self._local_data_only

        # if existing record type is INVITE, then ACCEPT or amend as new INVITE
        # else replace it with AMEND
        if self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE:
            if accept:
                new.record_type = MEMBERSHIP_RECORD_TYPE.ACCEPT
            else:
                new.record_type = MEMBERSHIP_RECORD_TYPE.INVITE
        else:
            new.record_type = MEMBERSHIP_RECORD_TYPE.AMEND

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
    def amend_by(self: MembershipType, actor: User):
        """Amend a membership in a `with` context."""
        return AmendMembership(self, actor)

    def merge_and_replace(
        self: MembershipType, actor: User, other: MembershipType
    ) -> MembershipType:
        """Replace this record by merging data from an independent record."""
        if self.__class__ is not other.__class__:
            raise TypeError("Merger requires membership records of the same type")
        if self.revoked_at is not None:
            raise MembershipRevokedError("This membership record has been revoked")
        if other.revoked_at is not None:
            raise MembershipRevokedError("Can't merge with a revoked membership record")

        if (
            self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE
            and other.record_type != MEMBERSHIP_RECORD_TYPE.INVITE
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

    @with_roles(call={'subject'})
    def accept(self: MembershipType, actor: User) -> MembershipType:
        """Accept a membership invitation."""
        if self.record_type != MEMBERSHIP_RECORD_TYPE.INVITE:
            raise MembershipRecordTypeError("This membership record is not an invite")
        if 'subject' not in self.roles_for(actor):
            raise ValueError("Invite must be accepted by the invited user")
        return self.replace(actor, accept=True)

    @with_roles(call={'owner', 'subject'})
    def freeze_subject_attribution(self: MembershipType, actor: User) -> MembershipType:
        """
        Freeze subject attribution and return a replacement record.

        Subclasses that support subject attribution must override this method. The
        default implementation returns `self`.
        """
        return self


@declarative_mixin
class ImmutableUserMembershipMixin(ImmutableMembershipMixin):
    """Support class for immutable memberships for users."""

    user_id: sa.Column[int]

    @declared_attr  # type: ignore[no-redef]
    def user_id(cls) -> sa.Column[int]:  # pylint: disable=no-self-argument
        """Foreign key column to user table."""
        return db.Column(
            None,
            sa.ForeignKey('user.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        )

    @with_roles(read={'subject', 'editor'}, grants={'subject'})
    @declared_attr
    def user(cls) -> Mapped[User]:  # pylint: disable=no-self-argument
        """User who is the subject of this membership record."""
        return immutable(sa.orm.relationship(User, foreign_keys=[cls.user_id]))

    subject: Mapped[User]

    @declared_attr  # type: ignore[no-redef]
    def subject(cls) -> Mapped[User]:  # pylint: disable=no-self-argument
        """Subject of this membership record."""
        return sa.orm.synonym('user')

    @declared_attr
    def __table_args__(cls) -> Mapped[tuple]:  # pylint: disable=no-self-argument
        """Table arguments for SQLAlchemy."""
        if cls.parent_id is not None:
            return (
                sa.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    cls.parent_id.name,
                    'user_id',
                    unique=True,
                    postgresql_where=sa.column('revoked_at').is_(None),
                ),
            )
        return (
            sa.Index(
                'ix_' + cls.__tablename__ + '_active',
                'user_id',
                unique=True,
                postgresql_where=sa.column('revoked_at').is_(None),
            ),
        )

    @hybrid_property
    def is_self_granted(self) -> bool:
        """Return True if the subject of this record is also the granting actor."""
        return self.user_id == self.granted_by_id

    with_roles(is_self_granted, read={'subject', 'editor'})

    @hybrid_property
    def is_self_revoked(self) -> bool:
        """Return True if the subject of this record is also the revoking actor."""
        return self.user_id == self.revoked_by_id

    with_roles(is_self_revoked, read={'subject', 'editor'})

    def copy_template(self: MembershipType, **kwargs) -> MembershipType:
        return type(self)(user=self.user, **kwargs)

    @classmethod
    def migrate_user(  # type: ignore[return]
        cls, old_user: User, new_user: User
    ) -> OptionalMigratedTables:
        """
        Migrate memberhip records from one user to another.

        If both users have active records, they are merged into a new record in the new
        user's favour. All revoked records for the old user are transferred to the new
        user.
        """
        # Look up all active membership records of the subclass's type for the old user
        # account. `cls` here represents the subclass.
        old_user_records = cls.query.filter(
            cls.user == old_user, cls.revoked_at.is_(None)
        ).all()
        # Look up all conflicting memberships for the new user account. Limit lookups by
        # parent except when the membership type doesn't have a parent (SiteMembership).
        if cls.parent_id is not None:
            new_user_records = cls.query.filter(
                cls.user == new_user,
                cls.revoked_at.is_(None),
                cls.parent_id.in_([r.parent_id for r in old_user_records]),
            ).all()
        else:
            new_user_records = cls.query.filter(
                cls.user == new_user,
                cls.revoked_at.is_(None),
            ).all()
        new_user_records_by_parent = {r.parent_id: r for r in new_user_records}

        for record in old_user_records:
            if record.parent_id in new_user_records_by_parent:
                # Where there is a conflict, merge the records
                new_user_records_by_parent[record.parent_id].merge_and_replace(
                    new_user, record
                )
                db.session.flush()

        # Transfer all revoked records and non-conflicting active records. At this point
        # no filter is necessary as the conflicting records have all been merged.
        cls.query.filter(cls.user == old_user).update(
            {'user_id': new_user.id}, synchronize_session=False
        )
        # Also update the revoked_by and granted_by user accounts
        cls.query.filter(cls.revoked_by == old_user).update(
            {'revoked_by_id': new_user.id}, synchronize_session=False
        )
        cls.query.filter(cls.granted_by == old_user).update(
            {'granted_by_id': new_user.id}, synchronize_session=False
        )
        db.session.flush()


@declarative_mixin
class ImmutableProfileMembershipMixin(ImmutableMembershipMixin):
    """Support class for immutable memberships for profiles."""

    profile_id: sa.Column[int]

    @declared_attr  # type: ignore[no-redef]
    def profile_id(cls) -> sa.Column[int]:  # pylint: disable=no-self-argument
        """Foreign key column to profile table."""
        return db.Column(
            None,
            sa.ForeignKey('profile.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        )

    @with_roles(read={'subject', 'editor'}, grants_via={None: {'admin': 'subject'}})
    @declared_attr
    def profile(  # pylint: disable=no-self-argument
        cls,
    ) -> sa.orm.relationship[Profile]:
        """Profile that is the subject of this membership record."""
        return immutable(sa.orm.relationship(Profile, foreign_keys=[cls.profile_id]))

    subject: Mapped[Profile]

    @declared_attr  # type: ignore[no-redef]
    def subject(  # pylint: disable=no-self-argument
        cls,
    ) -> Mapped[Profile]:
        """Subject of this membership record."""
        return sa.orm.synonym('profile')

    @declared_attr
    def __table_args__(cls) -> Mapped[tuple]:  # pylint: disable=no-self-argument
        if cls.parent_id is not None:
            return (
                sa.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    cls.parent_id.name,
                    'profile_id',
                    unique=True,
                    postgresql_where=sa.column('revoked_at').is_(None),
                ),
            )
        return (
            sa.Index(
                'ix_' + cls.__tablename__ + '_active',
                'profile_id',
                unique=True,
                postgresql_where=sa.column('revoked_at').is_(None),
            ),
        )

    @hybrid_property
    def is_self_granted(self) -> bool:
        """Return True if the subject of this record is also the granting actor."""
        return 'subject' in self.roles_for(self.granted_by)

    with_roles(is_self_granted, read={'subject', 'editor'})

    @hybrid_property
    def is_self_revoked(self) -> bool:
        """Return True if the subject of this record is also the revoking actor."""
        return 'subject' in self.roles_for(self.revoked_by)

    with_roles(is_self_revoked, read={'subject', 'editor'})

    def copy_template(self: MembershipType, **kwargs) -> MembershipType:
        return type(self)(profile=self.profile, **kwargs)

    @classmethod
    def migrate_profile(  # type: ignore[return]
        cls, old_profile: Profile, new_profile: Profile
    ) -> OptionalMigratedTables:
        """
        Migrate memberhip records from one profile to another.

        If both profiles have active records, they are merged into a new record in the
        new profile's favour. All revoked records for the old profile are transferred to
        the new profile.
        """
        # Look up all active membership records of the subclass's type for the old
        # profile. `cls` here represents the subclass.
        old_profile_records = cls.query.filter(
            cls.profile == old_profile, cls.revoked_at.is_(None)
        ).all()
        # Look up all conflicting memberships for the new profile. Limit lookups by
        # parent except when the membership type doesn't have a parent.
        if cls.parent_id is not None:
            new_profile_records = cls.query.filter(
                cls.profile == new_profile,
                cls.revoked_at.is_(None),
                cls.parent_id.in_([r.parent_id for r in old_profile_records]),
            ).all()
        else:
            new_profile_records = cls.query.filter(
                cls.profile == new_profile,
                cls.revoked_at.is_(None),
            ).all()
        new_profile_records_by_parent = {r.parent_id: r for r in new_profile_records}

        for record in old_profile_records:
            if record.parent_id in new_profile_records_by_parent:
                # Where there is a conflict, merge the records
                new_profile_records_by_parent[record.parent_id].merge_and_replace(
                    new_profile, record
                )
                db.session.flush()

        # Transfer all revoked records and non-conflicting active records. At this point
        # no filter is necessary as the conflicting records have all been merged.
        cls.query.filter(cls.profile == old_profile).update(
            {'profile_id': new_profile.id}, synchronize_session=False
        )
        db.session.flush()


@declarative_mixin
class ReorderMembershipMixin(ReorderMixin):
    """Customizes ReorderMixin for membership models."""

    seq: Mapped[int]

    #: Sequence number. Not immutable, and may be overwritten by ReorderMixin as a
    #: side-effect of reordering other records. This is not considered a revision.
    #: However, it can be argued that relocating a sponsor in the list constitutes a
    #: change that must be recorded as a revision. We may need to change our opinion
    #: on `seq` being mutable in a future iteration.
    @declared_attr  # type: ignore[no-redef]
    def seq(cls) -> Mapped[int]:  # pylint: disable=no-self-argument
        """Ordering sequence number."""
        return sa.Column(sa.Integer, nullable=False)

    @declared_attr
    def __table_args__(cls) -> Mapped[tuple]:  # pylint: disable=no-self-argument
        """Table arguments."""
        args = list(super().__table_args__)  # type: ignore[misc]
        # Add unique constraint on :attr:`seq` for active records
        args.append(
            sa.Index(
                'ix_' + cls.__tablename__ + '_seq',  # type: ignore[attr-defined]
                cls.parent_id.name,
                'seq',
                unique=True,
                postgresql_where=sa.column('revoked_at').is_(None),
            ),
        )
        return tuple(args)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Assign a default value to `seq`
        if self.seq is None:
            self.seq = (
                db.select([sa.func.coalesce(sa.func.max(self.__class__.seq) + 1, 1)])
                .where(self.parent_scoped_reorder_query_filter)
                .scalar_subquery()
            )

    @property
    def parent_scoped_reorder_query_filter(self) -> ColumnElement:
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
                cls.is_active,  # type: ignore[attr-defined]
            )
        return sa.and_(
            cls.parent == self.parent,  # type: ignore[attr-defined]
            cls.is_active,  # type: ignore[attr-defined]
        )


@declarative_mixin
class FrozenAttributionMixin:
    """Provides a `title` data column and support method to freeze it."""

    subject: SubjectType
    replace: Callable[..., FrozenAttributionType]
    _local_data_only: bool

    @declared_attr
    def _title(cls) -> sa.Column[sa.Unicode]:  # pylint: disable=no-self-argument
        """Create optional attribution title for this membership record."""
        return immutable(
            sa.Column(
                'title', sa.Unicode, sa.CheckConstraint("title <> ''"), nullable=True
            )
        )

    @property
    def title(self) -> str:
        """Attribution title for this record."""
        if self._local_data_only:
            return self._title  # This may be None
        return self._title or self.subject.title

    @title.setter
    def title(self, value: Optional[str]) -> None:
        """Set or clear custom attribution title."""
        self._title = value or None  # Don't set empty string

    @property
    def name(self):
        """Return subject's name."""
        return self.subject.name

    @property
    def pickername(self):
        """Return subject's pickername."""
        return self.subject.pickername

    @with_roles(call={'owner', 'subject'})
    def freeze_subject_attribution(
        self: FrozenAttributionType, actor: User
    ) -> FrozenAttributionType:
        """Freeze subject attribution and return a replacement record."""
        if self._title is None:
            membership: FrozenAttributionType = self.replace(
                actor=actor, title=self.subject.title
            )
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

    def __init__(self, membership: MembershipType, actor: User) -> None:
        """Create an amendment placeholder."""
        if membership.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        object.__setattr__(self, 'membership', membership)
        object.__setattr__(self, '_new', {})
        object.__setattr__(self, '_actor', actor)

    def __getattr__(self, attr: str) -> Any:
        """Get an attribute from the underlying record."""
        if attr in self._new:
            return self._new[attr]
        return getattr(self.membership, attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        """Set an amended value."""
        if attr not in self.membership.__data_columns__:
            raise AttributeError(f"{attr} cannot be set")
        self._new[attr] = value

    def __enter__(self) -> AmendMembership:
        """Enter a `with` context."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit a `with` context and replace the membership record."""
        if exc_type is None:
            object.__setattr__(
                self, 'membership', self.membership.replace(self._actor, **self._new)
            )

    def commit(self) -> MembershipType:
        """Commit and return a replacement record when not using a `with` context."""
        self.__exit__(None, None, None)
        return self.membership


@event.listens_for(EnumerateMembershipsMixin, 'mapper_configured', propagate=True)
def _confirm_enumerated_mixins(mapper, class_) -> None:
    """Confirm that the membership collection attributes actually exist."""
    expected_class = ImmutableMembershipMixin
    if issubclass(class_, User):
        expected_class = ImmutableUserMembershipMixin
    elif issubclass(class_, Profile):
        expected_class = ImmutableProfileMembershipMixin
    for source in (
        class_.__active_membership_attrs__,
        class_.__noninvite_membership_attrs__,
    ):
        for attr_name in source:
            relationship = getattr(class_, attr_name, None)
            if relationship is None:
                raise AttributeError(
                    f'{class_.__name__} does not have a relationship named'
                    f' {attr_name!r} targeting a subclass of {expected_class.__name__}'
                )
            if not issubclass(relationship.property.mapper.class_, expected_class):
                raise AttributeError(
                    f'{class_.__name__}.{attr_name} should be a relationship to a'
                    f' subclass of {expected_class.__name__}'
                )
