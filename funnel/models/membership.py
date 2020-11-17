from __future__ import annotations

from typing import Any, Dict, Iterable, Set

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import StateManager, immutable, with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, UuidMixin, db
from .user import User

__all__ = [
    'MEMBERSHIP_RECORD_TYPE',
    'MembershipError',
    'MembershipRevokedError',
    'MembershipRecordTypeError',
]


class MEMBERSHIP_RECORD_TYPE(LabeledEnum):  # NOQA: N801
    INVITE = (0, 'invite', __("Invite"))
    ACCEPT = (1, 'accept', __("Accept"))
    DIRECT_ADD = (2, 'direct_add', __("Direct add"))
    AMEND = (3, 'amend', __("Amend"))


class MembershipError(Exception):
    """Base class for membership errors."""


class MembershipRevokedError(MembershipError):
    pass


class MembershipRecordTypeError(MembershipError):
    pass


class ImmutableMembershipMixin(UuidMixin, BaseMixin):
    """Support class for immutable memberships."""

    __uuid_primary_key__ = True
    #: List of columns that will be copied into a new row when a membership is amended
    __data_columns__: Iterable[str] = ()
    #: Parent column (override as synonym of 'profile_id' or 'project_id' in the subclasses)
    parent_id = None

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
        return db.relationship(User, foreign_keys=[cls.user_id])

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

        This is nullable only for historical data. New records always require a value for granted_by
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
    def is_active(self):
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
    def is_invite(self):
        return self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE

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
        """Roles offered by this membership record."""
        return set()

    # Subclasses must gate these methods in __roles__

    @with_roles(call={'subject', 'editor'})
    def revoke(self, actor: User) -> None:
        if self.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        self.revoked_at = db.func.utcnow()
        self.revoked_by = actor

    @with_roles(call={'editor'})
    def replace(self, actor: User, **roles: Dict[str, Any]) -> ImmutableMembershipMixin:
        if self.revoked_at is not None:
            raise MembershipRevokedError(
                "This membership record has already been revoked"
            )
        if not set(roles.keys()).issubset(self.__data_columns__):
            raise AttributeError("Unknown role")

        # Perform sanity check. If nothing changed, just return self
        has_changes = False
        if self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE:
            # If we existing record is an INVITE, this must be an ACCEPT. This is an
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

        # if existing record type is INVITE, refuse to process
        # else replace it with AMEND
        if self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE:
            raise MembershipRecordTypeError("Invite must be revoked, not replaced")
        new.record_type = MEMBERSHIP_RECORD_TYPE.AMEND

        for column in self.__data_columns__:
            if column in roles:
                setattr(new, column, roles[column])
            else:
                setattr(new, column, getattr(self, column))
        db.session.add(new)
        return new

    @with_roles(call={'subject'})
    def accept(self, actor: User) -> ImmutableMembershipMixin:
        if self.record_type != MEMBERSHIP_RECORD_TYPE.INVITE:
            raise MembershipRecordTypeError("This membership record is not an invite")
        return self.replace(actor)
