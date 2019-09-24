# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from baseframe import __
from coaster.sqlalchemy import StateManager, immutable, with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, UuidMixin, db
from .user import User

__all__ = ['MEMBERSHIP_RECORD_TYPE']


class MEMBERSHIP_RECORD_TYPE(LabeledEnum):  # NOQA: N801
    INVITE = (0, 'invite', __(u"Invite"))
    ACCEPT = (1, 'accept', __("Accept"))
    DIRECT_ADD = (2, 'direct_add', __(u"Direct add"))
    AMEND = (3, 'amend', __(u"Amend"))


class ImmutableMembershipMixin(UuidMixin, BaseMixin):
    """
    Support class for immutable memberships
    """

    __uuid_primary_key__ = True
    #: List of columns that will be copied into a new row when a membership is amended
    __data_columns__ = ()
    #: Parent column ('profile_id' or 'project_id' in the subclasses)
    __parent_column__ = None

    #: Start time of membership, ordinarily a mirror of created_at except
    #: for records created when the member table was added to the database
    granted_at = immutable(
        db.Column(db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow())
    )
    #: End time of membership, ordinarily a mirror of updated_at
    revoked_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    #: Record type
    record_type = immutable(
        db.Column(
            db.Integer,
            StateManager.check_constraint('record_type', MEMBERSHIP_RECORD_TYPE),
            default=MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
            nullable=False,
        )
    )

    @declared_attr
    def revoked_by_id(cls):
        """Id of user who revoked the membership"""
        return db.Column(
            None, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
        )

    @declared_attr
    def revoked_by(cls):
        """User who revoked the membership"""
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

    @declared_attr
    def granted_by(cls):
        """User who assigned the membership"""
        return db.relationship(User, foreign_keys=[cls.granted_by_id])

    @hybrid_property
    def active(self):
        return self.revoked_at is None

    @active.expression
    def active(cls):  # NOQA: N805
        return cls.revoked_at.is_(None)

    @hybrid_property
    def is_invite(self):
        return self.record_type == MEMBERSHIP_RECORD_TYPE.INVITE

    @declared_attr
    def __table_args__(cls):
        return (
            db.Index(
                cls.__tablename__ + '_active',
                cls.__parent_column__,
                'user_id',
                unique=True,
                postgresql_where=db.text('revoked_at IS NULL'),
            ),
        )

    def offered_roles(self):
        """Roles offered by this membership record"""
        return set()

    # Subclasses must gate these methods in __roles__

    @with_roles(call={'subject', 'editor'})
    def revoke(self, actor):
        self.revoked_at = db.func.utcnow()
        self.revoked_by = actor

    @with_roles(call={'editor'})
    def replace(self, actor, record_type, **roles):
        if not set(roles.keys()).issubset(self.__data_columns__):
            raise AttributeError("Unknown role")
        self.revoked_at = db.func.utcnow()
        self.revoked_by = actor
        new = type(self)(user=self.user, granted_by=self.granted_by)

        # if existing record type is INVITE, let it be,
        # unless the new record type is ACCEPT.
        if self.record_type != MEMBERSHIP_RECORD_TYPE.INVITE:
            new.record_type = MEMBERSHIP_RECORD_TYPE.AMEND
        elif record_type == MEMBERSHIP_RECORD_TYPE.ACCEPT:
            new.record_type = MEMBERSHIP_RECORD_TYPE.ACCEPT

        setattr(new, self.__parent_column__, getattr(self, self.__parent_column__))
        for column in self.__data_columns__:
            if column in roles:
                setattr(new, column, roles[column])
            else:
                setattr(new, column, getattr(self, column))
        db.session.add(new)
        return new

    @with_roles(call={'subject'})
    def accept(self, actor):
        return self.replace(actor, record_type=MEMBERSHIP_RECORD_TYPE.ACCEPT)
