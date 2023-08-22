"""Project registration."""

from __future__ import annotations

from typing import Any, Dict

from coaster.sqlalchemy import immutable, with_roles

from . import Mapped, db, json_type, sa
from .membership_mixin import ActorMembershipMixin
from .project import Project

__all__ = ['Registration']


class Registration(ActorMembershipMixin, db.Model):  # type: ignore[name-defined]
    """A user can register on a project."""

    __tablename__ = 'registration'

    __data_columns__ = ActorMembershipMixin.__data_columns__ + ('form',)

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
            'number',
            'user',
            'project',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'number',
            'user',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'number',
        },
    }

    project_id: Mapped[int] = immutable(
        with_roles(
            sa.orm.mapped_column(
                None, sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False
            ),
            read={'subject', 'editor'},
        ),
    )
    project: Mapped[Project] = immutable(
        with_roles(
            sa.orm.relationship(
                Project,
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
    parent: Mapped[Project] = sa.orm.synonym('project')  # type: ignore[assignment]
    parent_id: Mapped[int] = sa.orm.synonym('project_id')  # type: ignore[assignment]
    parent_id_column = 'project_id'

    # Form response data, if registration is gated with a form
    form: Mapped[Dict[str, Any]] = immutable(
        with_roles(
            sa.orm.mapped_column(json_type, nullable=True),
            read={'owner', 'editor', 'subject'},
            write={'subject'},
        )
    )
