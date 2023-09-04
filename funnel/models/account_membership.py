"""Membership model for admins of an organization."""

from __future__ import annotations

from typing import Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import DynamicMapped, Mapped, Model, backref, relationship, sa
from .account import Account
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin

__all__ = ['AccountMembership']


class AccountMembership(ImmutableUserMembershipMixin, Model):
    """
    An account can be a member of another account as an owner, admin or follower.

    Owners can manage other administrators.

    TODO: This model may introduce non-admin memberships in a future iteration by
    replacing :attr:`is_owner` with :attr:`member_level` or distinct role flags as in
    :class:`ProjectMembership`.
    """

    __tablename__ = 'account_membership'
    __allow_unmapped__ = True

    # Legacy data has no granted_by
    __null_granted_by__ = True

    #: List of role columns in this model
    __data_columns__ = ('is_owner',)

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'member',
                'is_owner',
                'account',
                'granted_by',
                'revoked_by',
                'granted_at',
                'revoked_at',
                'is_self_granted',
                'is_self_revoked',
            }
        },
        'account_admin': {
            'read': {
                'record_type',
                'record_type_label',
                'granted_at',
                'granted_by',
                'revoked_at',
                'revoked_by',
                'member',
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
            'member',
            'account',
        },
        'without_parent': {'urls', 'uuid_b58', 'offered_roles', 'is_owner', 'member'},
        'related': {'urls', 'uuid_b58', 'offered_roles', 'is_owner'},
    }

    #: Organization that this membership is being granted on
    account_id: Mapped[int] = sa.orm.mapped_column(
        sa.Integer,
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
    )
    account: Mapped[Account] = with_roles(
        relationship(
            Account,
            foreign_keys=[account_id],
            backref=backref(
                'memberships', lazy='dynamic', cascade='all', passive_deletes=True
            ),
        ),
        grants_via={None: {'admin': 'account_admin', 'owner': 'account_owner'}},
    )
    parent_id: Mapped[int] = sa.orm.synonym('account_id')
    parent_id_column = 'account_id'
    parent: Mapped[Account] = sa.orm.synonym('account')

    # Organization roles:
    is_owner: Mapped[bool] = immutable(
        sa.orm.mapped_column(sa.Boolean, nullable=False, default=False)
    )

    @cached_property
    def offered_roles(self) -> Set[str]:
        """Roles offered by this membership record."""
        roles = {'admin'}
        if self.is_owner:
            roles.add('owner')
        return roles


# Add active membership relationships to Account
@reopen(Account)
class __Account:
    active_admin_memberships: DynamicMapped[AccountMembership] = with_roles(
        relationship(
            AccountMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                sa.orm.remote(AccountMembership.account_id) == Account.id,
                AccountMembership.is_active,
            ),
            order_by=AccountMembership.granted_at.asc(),
            viewonly=True,
        ),
        grants_via={'member': {'admin', 'owner'}},
    )

    active_owner_memberships: DynamicMapped[AccountMembership] = relationship(
        AccountMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(AccountMembership.account_id) == Account.id,
            AccountMembership.is_active,
            AccountMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_invitations: DynamicMapped[AccountMembership] = relationship(
        AccountMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(AccountMembership.account_id) == Account.id,
            AccountMembership.is_invite,
            AccountMembership.revoked_at.is_(None),
        ),
        viewonly=True,
    )

    owner_users = with_roles(
        DynamicAssociationProxy('active_owner_memberships', 'member'), read={'all'}
    )
    admin_users = with_roles(
        DynamicAssociationProxy('active_admin_memberships', 'member'), read={'all'}
    )

    # pylint: disable=invalid-unary-operand-type
    organization_admin_memberships: DynamicMapped[AccountMembership] = relationship(
        AccountMembership,
        lazy='dynamic',
        foreign_keys=[AccountMembership.member_id],  # type: ignore[has-type]
        viewonly=True,
    )

    noninvite_organization_admin_memberships: DynamicMapped[
        AccountMembership
    ] = relationship(
        AccountMembership,
        lazy='dynamic',
        foreign_keys=[AccountMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            ~AccountMembership.is_invite,
        ),
        viewonly=True,
    )

    active_organization_admin_memberships: DynamicMapped[
        AccountMembership
    ] = relationship(
        AccountMembership,
        lazy='dynamic',
        foreign_keys=[AccountMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            AccountMembership.is_active,
        ),
        viewonly=True,
    )

    active_organization_owner_memberships: DynamicMapped[
        AccountMembership
    ] = relationship(
        AccountMembership,
        lazy='dynamic',
        foreign_keys=[AccountMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            AccountMembership.is_active,
            AccountMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_organization_invitations: DynamicMapped[AccountMembership] = relationship(
        AccountMembership,
        lazy='dynamic',
        foreign_keys=[AccountMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            AccountMembership.is_invite,
            AccountMembership.revoked_at.is_(None),
        ),
        viewonly=True,
    )

    organizations_as_owner = DynamicAssociationProxy(
        'active_organization_owner_memberships', 'account'
    )

    organizations_as_admin = DynamicAssociationProxy(
        'active_organization_admin_memberships', 'account'
    )


Account.__active_membership_attrs__.add('active_organization_admin_memberships')
Account.__noninvite_membership_attrs__.add('noninvite_organization_admin_memberships')
