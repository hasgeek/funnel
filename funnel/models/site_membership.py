# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declared_attr

from . import User, db
from .membership import ImmutableMembershipMixin

__all__ = ['SiteMembership']


class SiteMembership(ImmutableMembershipMixin, db.Model):
    """
    Users can be site admin with different rights.
    """

    __tablename__ = 'site_membership'

    # List of is_role columns in this model
    __data_columns__ = {'is_comment_moderator'}

    __roles__ = {
        'all': {'read': {'urls', 'user', 'is_comment_moderator', 'is_user_moderator'}}
    }

    # Site admin roles (at least one must be True):

    #: Comment moderators can delete comments
    is_comment_moderator = db.Column(db.Boolean, nullable=False, default=False)
    #: User moderators can suspend users
    is_user_moderator = db.Column(db.Boolean, nullable=False, default=False)

    @declared_attr
    def __table_args__(cls):
        args = list(super().__table_args__)
        args.append(
            db.CheckConstraint(
                db.or_(
                    cls.is_comment_moderator.is_(True), cls.is_user_moderator.is_(True),
                ),
                name='site_membership_has_role',
            )
        )
        return tuple(args)

    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = set()
        if self.is_comment_moderator:
            roles.add('comment_moderator')
        if self.is_user_moderator:
            roles.add('user_moderator')
        roles.add('site_admin')
        return roles


def _is_comment_moderator(self):
    return (
        SiteMembership.query.filter_by(
            user=self, is_comment_moderator=True, is_active=True
        ).one_or_none()
        is not None
    )


def _is_user_moderator(self):
    return (
        SiteMembership.query.filter_by(
            user=self, is_user_moderator=True, is_active=True
        ).one_or_none()
        is not None
    )


User.is_comment_moderator = property(fget=_is_comment_moderator)
User.is_user_moderator = property(fget=_is_user_moderator)
