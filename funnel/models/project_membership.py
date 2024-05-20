"""Project crew and (future) participant registration membership."""

from __future__ import annotations

from werkzeug.utils import cached_property

from coaster.sqlalchemy import immutable, with_roles

from .base import Mapped, Model, declared_attr, relationship, sa, sa_orm
from .membership_mixin import ImmutableMembershipMixin
from .project import Project

__all__ = ['ProjectMembership', 'project_child_role_map', 'project_child_role_set']

#: Roles in a project and their remapped names in objects attached to a project
project_child_role_map: dict[str, str] = {
    'editor': 'project_editor',
    'promoter': 'project_promoter',
    'usher': 'project_usher',
    'crew': 'project_crew',
    'participant': 'project_participant',
    'reader': 'reader',
}

#: A model that is indirectly under a project needs the role names without remapping
project_child_role_set: set[str] = set(project_child_role_map.values())

#: ProjectMembership maps project's `account_admin` role to membership's `editor`
#: role in addition to the recurring role grant map
project_membership_role_map: dict[str, set[str]] = {
    'account_admin': {'account_admin', 'editor'}
}
project_membership_role_map.update(
    {k: {v} if isinstance(v, str) else v for k, v in project_child_role_map.items()}
)


class ProjectMembership(ImmutableMembershipMixin, Model):
    """Users can be crew members of projects, with specified access rights."""

    __tablename__ = 'project_membership'

    #: Legacy data has no granted_by
    __null_granted_by__ = True

    #: List of is_role columns in this model
    __data_columns__ = ('is_editor', 'is_promoter', 'is_usher', 'label')

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'member',
                'project',
                'is_editor',
                'is_promoter',
                'is_usher',
                'label',
                'bio',
            }
        },
        'project_crew': {
            'read': {
                'record_type_enum',
                'granted_at',
                'granted_by',
                'revoked_at',
                'revoked_by',
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
            'is_editor',
            'is_promoter',
            'is_usher',
            'label',
            'member',
            'project',
            'bio',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_editor',
            'is_promoter',
            'is_usher',
            'label',
            'member',
            'bio',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_editor',
            'is_promoter',
            'is_usher',
            'label',
            'bio',
        },
    }

    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('project.id', ondelete='CASCADE'), default=None, nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='crew_memberships'),
        grants_via={None: project_membership_role_map},
    )
    parent_id: Mapped[int] = sa_orm.synonym('project_id')
    parent_id_column = 'project_id'
    parent: Mapped[Project] = sa_orm.synonym('project')

    # Project crew roles (at least one must be True):

    #: Editors can edit all common and editorial details of an event
    is_editor: Mapped[bool] = sa_orm.mapped_column(default=False)
    #: Promoters are responsible for promotion and have write access
    #: to common details plus read access to everything else. Unlike
    #: editors, they cannot edit the schedule
    is_promoter: Mapped[bool] = sa_orm.mapped_column(default=False)
    #: Ushers help participants find their way around an event and have
    #: the ability to scan badges at the door
    is_usher: Mapped[bool] = sa_orm.mapped_column(default=False)

    #: Optional label, indicating the member's role in the project
    label: Mapped[str | None] = immutable(
        sa_orm.mapped_column(
            sa.CheckConstraint(
                "label <> ''", name='project_crew_membership_label_check'
            )
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
        args.append(
            sa.CheckConstraint(
                sa.or_(
                    cls.is_editor.is_(True),
                    cls.is_promoter.is_(True),
                    cls.is_usher.is_(True),
                ),
                name='project_crew_membership_has_role',
            )
        )
        if kwargs:
            args.append(kwargs)
        return tuple(args)

    @property
    def bio(self) -> str | None:
        """Member's biography line, from their account."""
        # TODO: Use the account membership label if available (requires discovery of
        # account membership instance)
        return self.member.tagline

    @cached_property
    def offered_roles(self) -> set[str]:
        """Roles offered by this membership record."""
        roles = {'crew', 'participant'}
        if self.is_editor:
            roles.add('editor')
        if self.is_promoter:
            roles.add('promoter')
        if self.is_usher:
            roles.add('usher')
        return roles
