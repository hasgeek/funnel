"""Membership model for admins of an organization."""

from __future__ import annotations

from typing import Set
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import Mapped, db, sa
from .account import Account
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin

__all__ = ['AccountAdminMembership']


class AccountAdminMembership(
    ImmutableUserMembershipMixin,
    db.Model,  # type: ignore[name-defined]
):
    """
    An account can be an owner or admin of another account.

    Owners can manage other administrators. This model may introduce non-admin
    memberships in a future iteration by replacing :attr:`is_owner` with
    :attr:`member_level` or distinct role flags as in :class:`ProjectCrewMembership`.
    """

    __tablename__ = 'account_admin_membership'
    __allow_unmapped__ = True

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
        'account_admin': {
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
    account_id: Mapped[int] = sa.orm.mapped_column(
        sa.Integer,
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
    )
    account: Mapped[Account] = with_roles(
        sa.orm.relationship(
            Account,
            foreign_keys=[account_id],
            backref=sa.orm.backref(
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
    active_admin_memberships = with_roles(
        sa.orm.relationship(
            AccountAdminMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                sa.orm.remote(AccountAdminMembership.account_id) == Account.id,
                AccountAdminMembership.is_active,  # type: ignore[arg-type]
            ),
            order_by=AccountAdminMembership.granted_at.asc(),
            viewonly=True,
        ),
        grants_via={'user': {'admin', 'owner'}},
    )

    active_owner_memberships = sa.orm.relationship(
        AccountAdminMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(AccountAdminMembership.account_id) == Account.id,
            AccountAdminMembership.is_active,  # type: ignore[arg-type]
            AccountAdminMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_invitations = sa.orm.relationship(
        AccountAdminMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            sa.orm.remote(AccountAdminMembership.account_id) == Account.id,
            AccountAdminMembership.is_invite,  # type: ignore[arg-type]
            AccountAdminMembership.revoked_at.is_(None),
        ),
        viewonly=True,
    )

    owner_users = with_roles(
        DynamicAssociationProxy('active_owner_memberships', 'user'), read={'all'}
    )
    admin_users = with_roles(
        DynamicAssociationProxy('active_admin_memberships', 'user'), read={'all'}
    )

    # pylint: disable=invalid-unary-operand-type
    organization_admin_memberships = sa.orm.relationship(
        AccountAdminMembership,
        lazy='dynamic',
        foreign_keys=[AccountAdminMembership.member_id],  # type: ignore[has-type]
        viewonly=True,
    )

    noninvite_organization_admin_memberships = sa.orm.relationship(
        AccountAdminMembership,
        lazy='dynamic',
        foreign_keys=[AccountAdminMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountAdminMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            ~AccountAdminMembership.is_invite,  # type: ignore[operator]
        ),
        viewonly=True,
    )

    active_organization_admin_memberships = sa.orm.relationship(
        AccountAdminMembership,
        lazy='dynamic',
        foreign_keys=[AccountAdminMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountAdminMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            AccountAdminMembership.is_active,  # type: ignore[arg-type]
        ),
        viewonly=True,
    )

    active_organization_owner_memberships = sa.orm.relationship(
        AccountAdminMembership,
        lazy='dynamic',
        foreign_keys=[AccountAdminMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountAdminMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            AccountAdminMembership.is_active,  # type: ignore[arg-type]
            AccountAdminMembership.is_owner.is_(True),
        ),
        viewonly=True,
    )

    active_organization_invitations = sa.orm.relationship(
        AccountAdminMembership,
        lazy='dynamic',
        foreign_keys=[AccountAdminMembership.member_id],
        primaryjoin=sa.and_(
            sa.orm.remote(AccountAdminMembership.member_id)  # type: ignore[has-type]
            == Account.id,
            AccountAdminMembership.is_invite,  # type: ignore[arg-type]
            AccountAdminMembership.revoked_at.is_(None),
        ),
        viewonly=True,
    )

    organizations_as_owner = DynamicAssociationProxy(
        'active_organization_owner_memberships', 'organization'
    )

    organizations_as_admin = DynamicAssociationProxy(
        'active_organization_admin_memberships', 'organization'
    )


Account.__active_membership_attrs__.add('active_organization_admin_memberships')
Account.__noninvite_membership_attrs__.add('noninvite_organization_admin_memberships')
