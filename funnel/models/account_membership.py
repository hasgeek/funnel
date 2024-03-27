"""Membership model for admins of an organization."""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from werkzeug.utils import cached_property

from coaster.sqlalchemy import immutable, with_roles

from .account import Account
from .base import Mapped, Model, declared_attr, relationship, sa, sa_orm
from .membership_mixin import ImmutableMembershipMixin

__all__ = ['AccountMembership']


class AccountMembership(ImmutableMembershipMixin, Model):
    """
    An account can be an owner, admin, member or follower of another account.

    Owners can manage other owners, admins and members, but not followers.
    """

    __tablename__ = 'account_membership'

    # Legacy data has no granted_by
    __null_granted_by__ = True

    #: List of role columns in this model
    __data_columns__ = ('is_admin', 'is_owner')

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'member',
                'is_admin',
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
            'is_admin',
            'is_owner',
            'member',
            'account',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_admin',
            'is_owner',
            'member',
        },
        'related': {'urls', 'uuid_b58', 'offered_roles', 'is_admin', 'is_owner'},
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
    is_admin: Mapped[bool] = immutable(sa_orm.mapped_column(default=False))
    # Default role if both are false: 'follower'

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple:  # type: ignore[override]
        """Table arguments."""
        try:
            args = list(super().__table_args__)
        except AttributeError:
            args = []
        kwargs = args.pop(-1) if args and isinstance(args[-1], dict) else None
        args.append(
            # Check if is_owner is True, is_admin must also be True
            sa.CheckConstraint(
                sa.or_(
                    sa.and_(
                        cls.is_owner.is_(True),
                        cls.is_admin.is_(True),
                    ),
                    cls.is_owner.is_(False),
                ),
                name='account_membership_owner_is_admin_check',
            )
        )
        if kwargs:
            args.append(kwargs)
        return tuple(args)

    @cached_property
    def offered_roles(self) -> set[str]:
        """Roles offered to the member via this membership record (if active)."""
        roles = {'follower'}
        if self.is_admin:
            roles |= {'admin', 'member'}
        if self.is_owner:
            roles |= {'owner', 'member'}
        return roles


@event.listens_for(AccountMembership.is_owner, 'set')
def _ensure_owner_is_admin_too(
    target: AccountMembership, value: Any, old_value: Any, _initiator: Any
) -> None:
    if value:
        target.is_admin = True
