"""Membership model for admins of an organization."""

from __future__ import annotations

from typing import Any, Self

from sqlalchemy import event
from werkzeug.utils import cached_property

from coaster.sqlalchemy import ImmutableColumnError, immutable, with_roles

from .account import Account
from .base import Mapped, Model, declared_attr, relationship, sa, sa_orm
from .membership_mixin import ImmutableMembershipMixin

__all__ = ['AccountMembership']


class AccountMembership(ImmutableMembershipMixin, Model):
    """
    An account can be an owner, admin or follower of another account.

    Owners can manage other owners and admins (members), but not followers. The term
    'member' has two distinct meanings in this model:

    1. The subject of an :class:`AccountMembership` record is referred to as a member,
       even if the record is revoked and therefore has no bearing on the parent
       :class:`Account`.
    2. The :class:`Account` model recognises a 'member' role that is granted via an
       :class:`AccountMembership` record, but only if specific flags are set (currently
       :attr:`is_admin`).
    """

    __tablename__ = 'account_membership'

    # Legacy data has no granted_by
    __null_granted_by__ = True

    #: List of role columns in this model
    __data_columns__ = ('is_follower', 'is_admin', 'is_owner', 'label')

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'offered_roles',
                'member',
                'is_admin',
                'is_owner',
                'is_follower',
                'label',
                'account',
                'granted_by',
                'revoked_by',
                'granted_at',
                'revoked_at',
                'is_self_granted',
                'is_self_revoked',
                'is_migrated',
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
                'is_migrated',
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
            'is_follower',
            'label',
            'member',
            'account',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_admin',
            'is_owner',
            'is_follower',
            'label',
            'member',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_admin',
            'is_owner',
            'is_follower',
            'label',
        },
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
    # This column tracks whether the member is explicitly a follower, or implicitly
    # via being an admin. If implicit, revoking admin status must also revoke follower
    # status
    is_follower: Mapped[bool] = immutable(sa_orm.mapped_column(default=False))

    #: Optional label, indicating the member's role in the account
    label: Mapped[str | None] = immutable(
        sa_orm.mapped_column(
            sa.CheckConstraint("label <> ''", name='account_membership_label_check')
        )
    )

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple:  # type: ignore[override]
        """Table arguments."""
        try:
            args = list(super().__table_args__)
        except AttributeError:
            args = []
        kwargs = args.pop(-1) if args and isinstance(args[-1], dict) else None
        args.extend(
            [
                # If is_owner is True, is_admin must also be True
                sa.CheckConstraint(
                    sa.or_(
                        sa.and_(
                            cls.is_owner.is_(True),
                            cls.is_admin.is_(True),
                        ),
                        cls.is_owner.is_(False),
                    ),
                    name='account_membership_owner_is_admin_check',
                ),
                # Either is_admin or is_follower must be True
                sa.CheckConstraint(
                    sa.or_(
                        cls.is_admin.is_(True),
                        cls.is_follower.is_(True),
                    ),
                    name='account_membership_admin_or_follower_check',
                ),
            ]
        )
        if kwargs:
            args.append(kwargs)
        return tuple(args)

    @cached_property
    def offered_roles(self) -> set[str]:
        """Roles offered to the member via this membership record (if active)."""
        # Admins and owners are always followers, and a record must have is_follower
        # or is_admin True, so this guarantees the `follower` role is always present
        roles = {'follower'}
        if self.is_admin:
            roles |= {'admin', 'member'}
        if self.is_owner:
            roles |= {'owner', 'member'}
        return roles

    @with_roles(call={'member'})
    def revoke_follower(self, actor: Account) -> Self | None:
        """Make the member unfollow (potentially revoking the membership)."""
        if self.is_admin:
            return self.replace(actor, is_follower=False)
        self.revoke(actor)
        return None

    @with_roles(call={'account_admin'})
    def revoke_member(self, actor: Account) -> Self | None:
        """Remove the member as admin/owner (potentially revoking the membership)."""
        if self.is_follower:
            return self.replace(actor, is_admin=False, is_owner=False)
        self.revoke(actor)
        return None


@event.listens_for(AccountMembership.is_owner, 'set')
def _ensure_owner_is_admin_too(
    target: AccountMembership, value: Any, old_value: Any, _initiator: Any
) -> None:
    if value:
        try:
            target.is_admin = True
        except ImmutableColumnError:
            # Bypass the protections of the immutable validator
            target.__dict__['is_admin'] = True
