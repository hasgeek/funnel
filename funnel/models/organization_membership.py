"""Membership model for admins of an organization."""

from __future__ import annotations

from typing import Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin
from .user import Organization, User

__all__ = ['OrganizationMembership']


class OrganizationMembership(ImmutableUserMembershipMixin, db.Model):
    """
    A user can be an administrator of an organization and optionally an owner.

    Owners can manage other administrators. This model may introduce non-admin
    memberships in a future iteration by replacing :attr:`is_owner` with
    :attr:`member_level` or distinct role flags as in :class:`ProjectMembership`.
    """

    __tablename__ = 'organization_membership'

    # Legacy data has no granted_by
    __null_granted_by__ = True

    #: List of role columns in this model
    __data_columns__ = ('is_owner',)

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'user',
                'is_owner',
                'organization',
                'granted_by',
                'revoked_by',
                'granted_at',
                'revoked_at',
                'is_self_granted',
                'is_self_revoked',
            }
        },
        'profile_admin': {
            'read': {
                'record_type',
                'granted_at',
                'granted_by',
                'revoked_at',
                'revoked_by',
                'user',
                'is_active',
                'is_invite',
                'is_self_granted',
                'is_self_revoked',
            }
        },
    }
    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_owner',
            'user',
            'organization',
        },
        'without_parent': {'urls', 'uuid_b58', 'offered_roles', 'is_owner', 'user'},
        'related': {'urls', 'uuid_b58', 'offered_roles', 'is_owner'},
    }

    #: Organization that this membership is being granted on
    organization_id = immutable(
        db.Column(
            None, db.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False
        )
    )
    organization = immutable(
        with_roles(
            db.relationship(
                Organization,
                backref=db.backref(
                    'memberships', lazy='dynamic', cascade='all', passive_deletes=True
                ),
            ),
            grants_via={None: {'admin': 'profile_admin', 'owner': 'profile_owner'}},
        )
    )
    parent = db.synonym('organization')
    parent_id = db.synonym('organization_id')

    # Organization roles:
    is_owner = immutable(db.Column(db.Boolean, nullable=False, default=False))

    @cached_property
    def offered_roles(self) -> Set[str]:
        """Roles offered by this membership record."""
        roles = {'admin'}
        if self.is_owner:
            roles.add('owner')
        return roles


# Add active membership relationships to Organization and User
# Organization.active_memberships is a future possibility. For now just admin and owner
@reopen(Organization)
class __Organization:
    active_admin_memberships = with_roles(
        db.relationship(
            OrganizationMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                db.remote(OrganizationMembership.organization_id) == Organization.id,
                OrganizationMembership.is_active,
            ),
            order_by=OrganizationMembership.granted_at.asc(),
            viewonly=True,
        ),
        grants_via={'user': {'admin', 'owner'}},
    )

    active_owner_memberships = db.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            db.remote(OrganizationMembership.organization_id) == Organization.id,
            OrganizationMembership.is_active,
            OrganizationMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_invitations = db.relationship(
        # pylint: disable=invalid-unary-operand-type
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            db.remote(OrganizationMembership.organization_id) == Organization.id,
            OrganizationMembership.is_invite,
            ~OrganizationMembership.is_active,  # type: ignore[operator]
        ),
        viewonly=True,
    )

    owner_users = with_roles(
        DynamicAssociationProxy('active_owner_memberships', 'user'), read={'all'}
    )
    admin_users = with_roles(
        DynamicAssociationProxy('active_admin_memberships', 'user'), read={'all'}
    )


# User.active_organization_memberships is a future possibility.
# For now just admin and owner
@reopen(User)
class __User:
    organization_admin_memberships = db.relationship(
        OrganizationMembership,
        lazy='dynamic',
        foreign_keys=[OrganizationMembership.user_id],
        viewonly=True,
    )

    active_organization_admin_memberships = db.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            db.remote(OrganizationMembership.user_id) == User.id,
            OrganizationMembership.is_active,
        ),
        viewonly=True,
    )

    active_organization_owner_memberships = db.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            db.remote(OrganizationMembership.user_id) == User.id,
            OrganizationMembership.is_active,
            OrganizationMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_organization_invitations = db.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            # pylint: disable=invalid-unary-operand-type
            db.remote(OrganizationMembership.user_id) == User.id,
            OrganizationMembership.is_invite,
            ~OrganizationMembership.is_active,  # type: ignore[operator]
        ),
        viewonly=True,
    )

    organizations_as_owner = DynamicAssociationProxy(
        'active_organization_owner_memberships', 'organization'
    )

    organizations_as_admin = DynamicAssociationProxy(
        'active_organization_admin_memberships', 'organization'
    )
