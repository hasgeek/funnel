"""Membership model for admins of an organization."""

from __future__ import annotations

from typing import Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db, sa
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin
from .user import Organization, User

__all__ = ['OrganizationMembership']


class OrganizationMembership(
    ImmutableUserMembershipMixin,
    db.Model,  # type: ignore[name-defined]
):
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
                'record_type_label',
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
    organization_id: sa.Column[int] = immutable(
        sa.Column(
            sa.Integer,
            sa.ForeignKey('organization.id', ondelete='CASCADE'),
            nullable=False,
        )
    )
    organization: sa.orm.relationship[Organization] = immutable(
        with_roles(
            sa.orm.relationship(
                Organization,
                backref=sa.orm.backref(
                    'memberships', lazy='dynamic', cascade='all', passive_deletes=True
                ),
            ),
            grants_via={None: {'admin': 'profile_admin', 'owner': 'profile_owner'}},
        )
    )
    parent = sa.orm.synonym('organization')
    parent_id = sa.orm.synonym('organization_id')

    # Organization roles:
    is_owner = immutable(sa.Column(sa.Boolean, nullable=False, default=False))

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
        sa.orm.relationship(
            OrganizationMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                sa.orm.remote(OrganizationMembership.organization_id)
                == Organization.id,
                OrganizationMembership.is_active,  # type: ignore[arg-type]
            ),
            order_by=OrganizationMembership.granted_at.asc(),
            viewonly=True,
        ),
        grants_via={'user': {'admin', 'owner'}},
    )

    active_owner_memberships = sa.orm.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(OrganizationMembership.organization_id) == Organization.id,
            OrganizationMembership.is_active,  # type: ignore[arg-type]
            OrganizationMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_invitations = sa.orm.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(OrganizationMembership.organization_id) == Organization.id,
            OrganizationMembership.is_invite,  # type: ignore[arg-type]
            OrganizationMembership.revoked_at.is_(None),
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
    # pylint: disable=invalid-unary-operand-type
    organization_admin_memberships = sa.orm.relationship(
        OrganizationMembership,
        lazy='dynamic',
        foreign_keys=[OrganizationMembership.user_id],  # type: ignore[has-type]
        viewonly=True,
    )

    noninvite_organization_admin_memberships = sa.orm.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(OrganizationMembership.user_id)  # type: ignore[has-type]
            == User.id,
            ~OrganizationMembership.is_invite,  # type: ignore[operator]
        ),
        viewonly=True,
    )

    active_organization_admin_memberships = sa.orm.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(OrganizationMembership.user_id)  # type: ignore[has-type]
            == User.id,
            OrganizationMembership.is_active,  # type: ignore[arg-type]
        ),
        viewonly=True,
    )

    active_organization_owner_memberships = sa.orm.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(OrganizationMembership.user_id)  # type: ignore[has-type]
            == User.id,
            OrganizationMembership.is_active,  # type: ignore[arg-type]
            OrganizationMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_organization_invitations = sa.orm.relationship(
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(OrganizationMembership.user_id)  # type: ignore[has-type]
            == User.id,
            OrganizationMembership.is_invite,  # type: ignore[arg-type]
            OrganizationMembership.revoked_at.is_(None),
        ),
        viewonly=True,
    )

    organizations_as_owner = DynamicAssociationProxy(
        'active_organization_owner_memberships', 'organization'
    )

    organizations_as_admin = DynamicAssociationProxy(
        'active_organization_admin_memberships', 'organization'
    )


User.__active_membership_attrs__.add('active_organization_admin_memberships')
User.__noninvite_membership_attrs__.add('noninvite_organization_admin_memberships')
