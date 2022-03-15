"""Base class for history-preserving membership records."""

from __future__ import annotations

from typing import Any, Iterable, Set, TypeVar

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql.expression import ClauseList

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import StateManager, immutable, with_roles
from coaster.utils import LabeledEnum

from ..typing import OptionalMigratedTables
from . import BaseMixin, UuidMixin, db, hybrid_property
from .profile import Profile
from .reorder_mixin import ReorderMixin
from .user import User

__all__ = [
    'MEMBERSHIP_RECORD_TYPE',
    'MembershipError',
    'MembershipRevokedError',
    'MembershipRecordTypeError',
]


MembershipType = TypeVar('MembershipType', bound='ImmutableMembershipMixin')


class MEMBERSHIP_RECORD_TYPE(LabeledEnum):
    """Membership record types."""

    INVITE = (0, 'invite', __("Invite"))
    ACCEPT = (1, 'accept', __("Accept"))
    DIRECT_ADD = (2, 'direct_add', __("Direct add"))
    AMEND = (3, 'amend', __("Amend"))


class MembershipError(Exception):
    """Base class for membership errors."""


class MembershipRevokedError(MembershipError):
    """Membership record has already been revoked."""


class MembershipRecordTypeError(MembershipError):
    """Membership record type is invalid."""


class ImmutableMembershipMixin(UuidMixin, BaseMixin):
    """Support class for immutable memberships."""

    __uuid_primary_key__ = True
    #: Can granted_by be null? Only in memberships based on legacy data
    __null_granted_by__ = False
    #: List of columns that will be copied into a new row when a membership is amended
    __data_columns__: Iterable[str] = ()
    #: Parent column (declare as synonym of 'profile_id' or 'project_id' in subclasses)
    parent_id: db.Column
    #: Subject of this membership (subclasses must define)
    subject = None

    #: Start time of membership, ordinarily a mirror of created_at except
    #: for records created when the member table was added to the database
    granted_at: db.Column = immutable(
        with_roles(
            db.Column(
                db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
            ),
            read={'subject', 'editor'},
        )
    )
    #: End time of membership, ordinarily a mirror of updated_at
    revoked_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True),
        read={'subject', 'editor'},
    )
    #: Record type
    record_type: db.Column = immutable(
        with_roles(
            db.Column(
                db.Integer,
                StateManager.check_constraint('record_type', MEMBERSHIP_RECORD_TYPE),
                default=MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                nullable=False,
            ),
            read={'subject', 'editor'},
        )
    )

    @declared_attr
    def revoked_by_id(cls):
        """Id of user who revoked the membership."""
        return db.Column(
            None, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
        )

    @with_roles(read={'subject', 'editor'}, grants={'editor'})
    @declared_attr
    def revoked_by(cls):
        """User who revoked the membership."""
        return db.relationship(User, foreign_keys=[cls.revoked_by_id])

    @declared_attr
    def granted_by_id(cls):
        """
        Id of user who assigned the membership.

        This is nullable only for historical data. New records always require a value
        for granted_by.
        """
        return db.Column(
            None,
            db.ForeignKey('user.id', ondelete='SET NULL'),
            nullable=cls.__null_granted_by__,
        )

    @with_roles(read={'subject', 'editor'}, grants={'editor'})
    @declared_attr
    def granted_by(cls):
        """User who assigned the membership."""
        return db.relationship(User, foreign_keys=[cls.granted_by_id])

    @hybrid_property
    def is_active(self) -> bool:
        return (
            self.revoked_at is None
            and self.record_type != MEMBERSHIP_RECORD_TYPE.INVITE
        )

    @is_active.expression
    def is_active(cls):
        return db.and_(
            cls.revoked_at.is_(None), cls.record_type != MEMBERSHIP_RECORD_TYPE.INVITE
        )

    with_roles(is_active, read={'subject'})

    @hybrid_property
    def is_invite(self) -> bool:
        return self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE

    with_roles(is_invite, read={'subject', 'editor'})

    def __repr__(self):
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
        self.revoked_at = db.func.utcnow()
        self.revoked_by = actor

    def copy_template(self: MembershipType, **kwargs) -> MembershipType:
        """Make a copy of self for customization."""
        raise NotImplementedError("Subclasses must implement copy_template")

    @with_roles(call={'editor'})
    def replace(
        self: MembershipType, actor: User, accept=False, **roles: object
    ) -> MembershipType:
        """Replace this membership record with changes to role columns."""
        if self.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        if not set(roles.keys()).issubset(self.__data_columns__):
            raise AttributeError("Unknown role")

        # Perform sanity check. If nothing changed, just return self
        has_changes = False
        if self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE:
            # If the existing record is an INVITE, this must be an ACCEPT. This is an
            # acceptable change
            has_changes = True
        else:
            # If it's not an ACCEPT, are the supplied roles different from existing?
            for column in roles:
                if roles[column] != getattr(self, column):
                    has_changes = True
        if not has_changes:
            # Nothing is changing. This is probably a form submit with no changes.
            # Do nothing and return self
            return self

        # An actual change? Revoke this record and make a new record

        self.revoked_at = db.func.utcnow()
        self.revoked_by = actor
        new = self.copy_template(parent_id=self.parent_id, granted_by=self.granted_by)

        # if existing record type is INVITE, then ACCEPT or amend as new INVITE
        # else replace it with AMEND
        if self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE:
            if accept:
                new.record_type = MEMBERSHIP_RECORD_TYPE.ACCEPT
            else:
                new.record_type = MEMBERSHIP_RECORD_TYPE.INVITE
        else:
            new.record_type = MEMBERSHIP_RECORD_TYPE.AMEND

        for column in self.__data_columns__:
            if column in roles:
                setattr(new, column, roles[column])
            else:
                setattr(new, column, getattr(self, column))
        db.session.add(new)
        return new

    @with_roles(call={'editor'})
    def amend_by(self: MembershipType, actor: User):
        """Amend a membership in a `with` context."""
        return AmendMembership(self, actor)

    def merge_and_replace(
        self: MembershipType, actor: User, other: MembershipType
    ) -> MembershipType:
        """Replace this record by merging roles from an independent record."""
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

        role_columns = {}
        for column in this.__data_columns__:
            column_value = getattr(this, column)
            if not column_value:
                # Replace falsy values with value from the other record. This may need
                # a more robust mechanism in the future if there are multi-value columns
                column_value = getattr(other, column)
            role_columns[column] = column_value
        replacement = this.replace(actor, **role_columns)
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


class ImmutableUserMembershipMixin(ImmutableMembershipMixin):
    """Support class for immutable memberships for users."""

    # mypy type declaration
    user_id: db.Column
    __table_args__: tuple

    @declared_attr  # type: ignore[no-redef]
    def user_id(cls):  # skipcq: PYL-E0102
        return db.Column(
            None,
            db.ForeignKey('user.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        )

    @with_roles(read={'subject', 'editor'}, grants={'subject'})
    @declared_attr
    def user(cls):
        return immutable(db.relationship(User, foreign_keys=[cls.user_id]))

    @declared_attr
    def subject(cls):
        return db.synonym('user')

    @declared_attr  # type: ignore[no-redef]
    def __table_args__(cls):
        if cls.parent_id is not None:
            return (
                db.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    cls.parent_id.name,
                    'user_id',
                    unique=True,
                    postgresql_where=db.column('revoked_at').is_(None),
                ),
            )
        else:
            return (
                db.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    'user_id',
                    unique=True,
                    postgresql_where=db.column('revoked_at').is_(None),
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
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
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
        return None


class ImmutableProfileMembershipMixin(ImmutableMembershipMixin):
    """Support class for immutable memberships for profiles."""

    # mypy type declaration
    profile_id: db.Column
    __table_args__: tuple

    @declared_attr  # type: ignore[no-redef]
    def profile_id(cls):  # skipcq: PYL-E0102
        return db.Column(
            None,
            db.ForeignKey('profile.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        )

    @with_roles(read={'subject', 'editor'}, grants_via={None: {'admin': 'subject'}})
    @declared_attr
    def profile(cls):
        return immutable(db.relationship(Profile, foreign_keys=[cls.profile_id]))

    @declared_attr
    def subject(cls):
        return db.synonym('profile')

    @declared_attr  # type: ignore[no-redef]
    def __table_args__(cls) -> tuple:
        if cls.parent_id is not None:
            return (
                db.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    cls.parent_id.name,
                    'profile_id',
                    unique=True,
                    postgresql_where=db.column('revoked_at').is_(None),
                ),
            )
        else:
            return (
                db.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    'profile_id',
                    unique=True,
                    postgresql_where=db.column('revoked_at').is_(None),
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
    def migrate_profile(
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
        return None


class ReorderMembershipMixin(ReorderMixin):
    """Customizes ReorderMixin for membership models."""

    # mypy type declaration
    seq: db.Column
    parent_id: db.Column
    __table_args__: tuple

    #: Sequence number. Not immutable, and may be overwritten by ReorderMixin as a
    #: side-effect of reordering other records. This is not considered a revision.
    #: However, it can be argued that relocating a sponsor in the list constitutes a
    #: change that must be recorded as a revision. We may need to change our opinion
    #: on `seq` being mutable in a future iteration.
    @declared_attr  # type: ignore[no-redef]
    def seq(cls) -> db.Column:
        return db.Column(db.Integer, nullable=False)

    @declared_attr  # type: ignore[no-redef]
    def __table_args__(cls) -> tuple:
        """Table arguments."""
        args = list(super().__table_args__)  # type: ignore[misc]
        # Add unique constraint on :attr:`seq` for active records
        args.append(
            db.Index(
                'ix_' + cls.__tablename__ + '_seq',  # type: ignore[attr-defined]
                cls.parent_id.name,
                'seq',
                unique=True,
                postgresql_where=db.column('revoked_at').is_(None),
            ),
        )
        return tuple(args)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)  # type: ignore[call-arg]
        # Assign a default value to `seq`
        if self.seq is None:
            self.seq = (
                db.select([db.func.coalesce(db.func.max(self.__class__.seq) + 1, 1)])
                .where(self.parent_scoped_reorder_query_filter)
                .scalar_subquery()
            )

    @property
    def parent_scoped_reorder_query_filter(self) -> ClauseList:
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
            return db.and_(
                cls.parent_id == self.parent_id,
                cls.is_active,  # type: ignore[attr-defined]
            )
        return db.and_(
            cls.parent == self.parent,  # type: ignore[attr-defined]
            cls.is_active,  # type: ignore[attr-defined]
        )


class AmendMembership:
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

    def __init__(self, membership: MembershipType, actor: User):
        """Create an amendment placeholder."""
        if membership.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        object.__setattr__(self, 'membership', membership)
        object.__setattr__(self, '_new', {})
        object.__setattr__(self, '_actor', actor)

    def __getattr__(self, attr: str):
        """Get an attribute from the underlying record."""
        if attr in self._new:
            return self._new[attr]
        return getattr(self.membership, attr)

    def __setattr__(self, attr: str, value: Any):
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

    def commit(self):
        """Commit and return a replacement record when not using a `with` context."""
        self.__exit__(None, None, None)
        return self.membership
