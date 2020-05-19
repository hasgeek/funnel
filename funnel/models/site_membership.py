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
    __data_columns__ = {'is_comment_moderator', 'is_user_moderator', 'is_site_editor'}

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'user',
                'is_comment_moderator',
                'is_user_moderator',
                'is_site_editor',
            }
        }
    }

    # Site admin roles (at least one must be True):

    #: Comment moderators can delete comments
    is_comment_moderator = db.Column(db.Boolean, nullable=False, default=False)
    #: User moderators can suspend users
    is_user_moderator = db.Column(db.Boolean, nullable=False, default=False)
    #: Site editors can feature or reject projects
    is_site_editor = db.Column(db.Boolean, nullable=False, default=False)

    @declared_attr
    def __table_args__(cls):
        args = list(super().__table_args__)
        args.append(
            db.CheckConstraint(
                db.or_(
                    cls.is_comment_moderator.is_(True),
                    cls.is_user_moderator.is_(True),
                    cls.is_site_editor.is_(True),
                ),
                name='site_membership_has_role',
            )
        )
        return tuple(args)

    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = {'site_admin'}
        if self.is_comment_moderator:
            roles.add('comment_moderator')
        if self.is_user_moderator:
            roles.add('user_moderator')
        if self.is_site_editor:
            roles.add('site_editor')
        return roles


User.is_comment_moderator = db.column_property(
    db.select([SiteMembership.is_comment_moderator])
    .where(SiteMembership.is_active == True)  # NOQA
    .where(SiteMembership.user_id == User.id)
    .correlate_except(SiteMembership)
)


User.is_user_moderator = db.column_property(
    db.select([SiteMembership.is_user_moderator])
    .where(SiteMembership.is_active == True)  # NOQA
    .where(SiteMembership.user_id == User.id)
    .correlate_except(SiteMembership)
)


User.is_site_editor = db.column_property(
    db.select([SiteMembership.is_site_editor])
    .where(SiteMembership.is_active == True)  # NOQA
    .where(SiteMembership.user_id == User.id)
    .correlate_except(SiteMembership)
)


User.active_site_memberships = db.relationship(
    SiteMembership,
    lazy='dynamic',
    primaryjoin=db.and_(SiteMembership.user_id == User.id, SiteMembership.is_active),
    viewonly=True,
)
