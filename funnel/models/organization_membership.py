from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db
from .helpers import reopen
from .membership import ImmutableMembershipMixin
from .user import Organization, User

__all__ = ['OrganizationMembership']


class OrganizationMembership(ImmutableMembershipMixin, db.Model):
    """
    A user can be an administrator of an organization and optionally an owner.
    Owners can manage other administrators. This model may introduce non-admin
    memberships in a future iteration by replacing :attr:`is_owner` with
    :attr:`member_level` or distinct role flags as in :class:`ProjectMembership`.
    """

    __tablename__ = 'organization_membership'

    # List of role columns in this model
    __data_columns__ = ('is_owner',)

    __roles__ = {
        'all': {'read': {'urls', 'user', 'is_owner', 'organization'}},
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
    parent = immutable(db.synonym('organization'))
    parent_id = immutable(db.synonym('organization_id'))

    # Organization roles:
    is_owner = immutable(db.Column(db.Boolean, nullable=False, default=False))

    @cached_property
    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = {'admin'}
        if self.is_owner:
            roles.add('owner')
        return roles


# Add active membership relationships to Organization and User
# Organization.active_memberships is a future possibility. For now just admin and owner
@reopen(Organization)
class Organization:  # type: ignore[no-redef]
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
        OrganizationMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            db.remote(OrganizationMembership.organization_id) == Organization.id,
            OrganizationMembership.is_invite,
            ~OrganizationMembership.is_active,
        ),
        viewonly=True,
    )

    owner_users = DynamicAssociationProxy('active_owner_memberships', 'user')
    admin_users = DynamicAssociationProxy('active_admin_memberships', 'user')


# User.active_organization_memberships is a future possibility.
# For now just admin and owner
@reopen(User)
class User:  # type: ignore[no-redef]
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
            db.remote(OrganizationMembership.user_id) == User.id,
            OrganizationMembership.is_invite,
            ~OrganizationMembership.is_active,
        ),
        viewonly=True,
    )

    organizations_as_owner = DynamicAssociationProxy(
        'active_organization_owner_memberships', 'organization'
    )

    organizations_as_admin = DynamicAssociationProxy(
        'active_organization_admin_memberships', 'organization'
    )
