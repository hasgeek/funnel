"""Membership model for admins of an organization."""

from __future__ import annotations

from werkzeug.utils import cached_property

from coaster.sqlalchemy import immutable, with_roles

from . import Mapped, Model, relationship, sa, sa_orm
from .account import Account
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
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer,
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
    )
    account: Mapped[Account] = with_roles(
        relationship(Account, foreign_keys=[account_id], back_populates='memberships'),
        grants_via={None: {'admin': 'account_admin', 'owner': 'account_owner'}},
    )
    parent_id: Mapped[int] = sa_orm.synonym('account_id')
    parent_id_column = 'account_id'
    parent: Mapped[Account] = sa_orm.synonym('account')

    # Organization roles:
    is_owner: Mapped[bool] = immutable(
        sa_orm.mapped_column(sa.Boolean, nullable=False, default=False)
    )

    @cached_property
    def offered_roles(self) -> set[str]:
        """Roles offered by this membership record."""
        roles = {'admin'}
        if self.is_owner:
            roles.add('owner')
        return roles
