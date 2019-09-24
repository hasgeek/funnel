# -*- coding: utf-8 -*-

from sqlalchemy.ext.associationproxy import association_proxy

from coaster.sqlalchemy import immutable, with_roles

from . import db
from .membership import ImmutableMembershipMixin
from .profile import Profile
from .user import User

__all__ = ['ProfileAdminMembership']


class ProfileAdminMembership(ImmutableMembershipMixin, db.Model):
    """
    A users can be an administrator of a profile and optionally an owner.
    Owners can manage other administrators.
    """

    __tablename__ = 'profile_admin_membership'

    # List of role columns in this model
    __data_columns__ = ('is_owner',)
    __parent_column__ = 'profile_id'

    __roles__ = {
        'all': {'read': {'user_details', 'is_owner', 'profile'}, 'call': {'url_for'}},
        'editor': {'read': {'edit_url', 'delete_url'}},
    }

    #: Profile that this membership is being granted on
    profile_id = immutable(
        db.Column(None, db.ForeignKey('profile.id', ondelete='CASCADE'), nullable=False)
    )
    profile = immutable(
        db.relationship(
            Profile,
            backref=db.backref(
                'admin_memberships',
                lazy='dynamic',
                cascade='all, delete-orphan',
                passive_deletes=True,
            ),
        )
    )
    parent = immutable(db.synonym('profile'))

    #: User who is an admin or owner
    user_id = immutable(
        db.Column(
            None,
            db.ForeignKey('user.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        )
    )
    user = with_roles(
        immutable(
            db.relationship(
                User,
                foreign_keys=[user_id],
                backref=db.backref(
                    'profile_admin_memberships',
                    lazy='dynamic',
                    cascade='all, delete-orphan',
                    passive_deletes=True,
                ),
            )
        ),
        grants={'subject'},
    )

    # Profile roles:
    is_owner = immutable(db.Column(db.Boolean, nullable=False, default=False))

    @property
    def user_details(self):
        return {
            'fullname': self.user.fullname,
            'username': self.user.username,
            'avatar': self.user.avatar,
        }

    @property
    def edit_url(self):
        return self.url_for('edit', _external=True)

    @property
    def delete_url(self):
        return self.url_for('delete', _external=True)

    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = {'profile_admin'}
        if self.is_owner:
            roles.add('profile_owner')
        return roles

    def roles_for(self, actor, anchors=()):
        """Roles available to the specified actor and anchors"""
        roles = super(ProfileAdminMembership, self).roles_for(actor, anchors)
        if 'profile_admin' in self.profile.roles_for(actor, anchors):
            roles.add('editor')
        return roles


# Add active membership relationships to Profile and User

Profile.active_admin_memberships = db.relationship(
    ProfileAdminMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProfileAdminMembership.profile_id == Profile.id,
        ProfileAdminMembership.active,
        ~ProfileAdminMembership.is_invite,
    ),
)

Profile.active_owner_memberships = db.relationship(
    ProfileAdminMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProfileAdminMembership.profile_id == Profile.id,
        ProfileAdminMembership.active,
        ProfileAdminMembership.is_owner.is_(True),
        ~ProfileAdminMembership.is_invite,
    ),
)

Profile.active_invitations = db.relationship(
    ProfileAdminMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProfileAdminMembership.profile_id == Profile.id,
        ProfileAdminMembership.is_invite,
    ),
)

User.active_profile_admin_memberships = db.relationship(
    ProfileAdminMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProfileAdminMembership.user_id == User.id,
        ProfileAdminMembership.active,
        ~ProfileAdminMembership.is_invite,
    ),
)

User.active_profile_owner_memberships = db.relationship(
    ProfileAdminMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProfileAdminMembership.user_id == User.id,
        ProfileAdminMembership.active,
        ProfileAdminMembership.is_owner.is_(True),
        ~ProfileAdminMembership.is_invite,
    ),
)

User.active_profile_invitations = db.relationship(
    ProfileAdminMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProfileAdminMembership.user_id == User.id, ProfileAdminMembership.is_invite
    ),
)

User.profiles_owned = association_proxy('active_profile_owner_memberships', 'profile')
