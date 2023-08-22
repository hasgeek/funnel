"""Project registration."""

from __future__ import annotations

from coaster.sqlalchemy import immutable, with_roles

from . import Mapped, db, sa
from .membership_mixin import ActorMembershipMixin
from .profile import Profile

__all__ = ['Follower']


class Follower(ActorMembershipMixin, db.Model):  # type: ignore[name-defined]
    """A user can register on a project."""

    __tablename__ = 'follower'

    __roles__ = {
        'all': {
            'read': {'urls', 'user'},
            'call': {'url_for'},
        },
    }
    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'user',
            'project',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'user',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
        },
    }

    profile_id: Mapped[int] = immutable(
        with_roles(
            sa.orm.mapped_column(
                None, sa.ForeignKey('profile.id', ondelete='CASCADE'), nullable=False
            ),
            read={'subject', 'editor'},
        ),
    )
    profile: Mapped[Profile] = immutable(
        with_roles(
            sa.orm.relationship(
                Profile,
                backref=sa.orm.backref(
                    'all_memberships',
                    lazy='dynamic',
                    cascade='all',
                    passive_deletes=True,
                ),
            ),
            read={'subject', 'editor'},
            grants_via={None: {'editor'}},
        ),
    )
    parent: Mapped[Profile] = sa.orm.synonym('profile')  # type: ignore[assignment]
    parent_id: Mapped[int] = sa.orm.synonym('profile_id')  # type: ignore[assignment]
    parent_id_column = 'profile_id'
