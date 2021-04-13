"""Base class for history-preserving membership records."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Set, TypeVar

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import StateManager, immutable, with_roles
from coaster.utils import LabeledEnum

from ..typing import OptionalMigratedTables
from . import BaseMixin, UuidMixin, db
from .user import User

__all__ = [
    'MEMBERSHIP_RECORD_TYPE',
    'MembershipError',
    'MembershipRevokedError',
    'MembershipRecordTypeError',
]


MembershipType = TypeVar('MembershipType', bound='ImmutableMembershipMixin')


class MEMBERSHIP_RECORD_TYPE(LabeledEnum):  # NOQA: N801
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
    #: List of columns that will be copied into a new row when a membership is amended
    __data_columns__: Iterable[str] = ()
    #: Parent column (declare as synonym of 'profile_id' or 'project_id' in subclasses)
    parent_id: db.Column

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
    record_type = immutable(
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

    # mypy type declaration
    user_id: db.Column

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
            None, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
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

    @is_active.expression  # type: ignore[no-redef]
    def is_active(cls):  # NOQA: N805
        return db.and_(
            cls.revoked_at.is_(None), cls.record_type != MEMBERSHIP_RECORD_TYPE.INVITE
        )

    with_roles(is_active, read={'subject'})

    @with_roles(read={'subject', 'editor'})
    @hybrid_property
    def is_invite(self) -> bool:
        return self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE

    @with_roles(read={'subject', 'editor'})
    @hybrid_property
    def is_self_granted(self) -> bool:
        """Return True if the subject of this record is also the granting actor."""
        return self.user_id == self.granted_by_id

    @with_roles(read={'subject', 'editor'})
    @hybrid_property
    def is_self_revoked(self) -> bool:
        """Return True if the subject of this record is also the revoking actor."""
        return self.user_id == self.revoked_by_id

    @declared_attr
    def __table_args__(cls):
        if cls.parent_id is not None:
            return (
                db.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    cls.parent_id.name,
                    'user_id',
                    unique=True,
                    postgresql_where=db.text('revoked_at IS NULL'),
                ),
            )
        else:
            return (
                db.Index(
                    'ix_' + cls.__tablename__ + '_active',
                    'user_id',
                    unique=True,
                    postgresql_where=db.text('revoked_at IS NULL'),
                ),
            )

    @cached_property
    def offered_roles(self) -> Set:
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

    @with_roles(call={'editor'})
    def replace(
        self, actor: User, accept=False, **roles: Dict[str, Any]
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
        new = type(self)(
            user=self.user, parent_id=self.parent_id, granted_by=self.granted_by
        )

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

    def merge_and_replace(self, actor: User, other: MembershipType) -> MembershipType:
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
    def accept(self, actor: User) -> MembershipType:
        """Accept a membership invitation."""
        if self.record_type != MEMBERSHIP_RECORD_TYPE.INVITE:
            raise MembershipRecordTypeError("This membership record is not an invite")
        if actor != self.user:
            raise ValueError("Invite must be accepted by the invited user")
        return self.replace(actor, accept=True)

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
        db.session.flush()
        return None
