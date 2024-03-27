"""Membership model for admins of an organization."""

from __future__ import annotations

from werkzeug.utils import cached_property

from coaster.sqlalchemy import immutable, with_roles

from .account import Account
from .base import Mapped, Model, relationship, sa, sa_orm
from .membership_mixin import ImmutableMembershipMixin

__all__ = ['AccountMembership']


class AccountMembership(ImmutableMembershipMixin, Model):
    """
    An account can be an owner, admin, member or follower of another account.

    Owners can manage other owners, admins and members, but not followers.

    TODO: Distinct flags for is_member, is_follower and is_admin.
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
                'record_type_enum',
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

    #: Account that this membership is being granted on
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        default=None,
        nullable=False,
    )
    account: Mapped[Account] = with_roles(
        relationship(foreign_keys=[account_id], back_populates='memberships'),
        grants_via={None: {'admin': 'account_admin', 'owner': 'account_owner'}},
    )
    parent_id: Mapped[int] = sa_orm.synonym('account_id')
    parent_id_column = 'account_id'
    parent: Mapped[Account] = sa_orm.synonym('account')

    # Organization roles:
    is_owner: Mapped[bool] = immutable(sa_orm.mapped_column(default=False))

    @cached_property
    def offered_roles(self) -> set[str]:
        """Roles offered by this membership record."""
        # TODO: is_member and is_admin will be distinct flags in the future, with the
        # base role set to `follower` only. is_owner will remain, but if it's set, then
        # is_admin must also be set (enforced with a check constraint)
        roles = {'follower', 'member', 'admin'}
        if self.is_owner:
            roles.add('owner')
        return roles
