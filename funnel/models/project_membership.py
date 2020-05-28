from sqlalchemy.ext.declarative import declared_attr

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db
from .membership import ImmutableMembershipMixin
from .project import Project
from .user import User

try:
    from functools import cached_property
except ImportError:
    from werkzeug.utils import cached_property

__all__ = ['ProjectCrewMembership', 'project_child_role_map']

# Roles in a project and their remapped names in objects attached to a project
project_child_role_map = {
    'editor': 'project_editor',
    'concierge': 'project_concierge',
    'usher': 'project_usher',
    'crew': 'project_crew',
    'participant': 'project_participant',
}


class ProjectCrewMembership(ImmutableMembershipMixin, db.Model):
    """
    Users can be crew members of projects, with specified access rights.
    """

    __tablename__ = 'project_crew_membership'

    # List of is_role columns in this model
    __data_columns__ = ('is_editor', 'is_concierge', 'is_usher')

    __roles__ = {
        'all': {
            'read': {'urls', 'user', 'is_editor', 'is_concierge', 'is_usher', 'project'}
        }
    }
    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_editor',
            'is_concierge',
            'is_usher',
            'user',
            'project',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_editor',
            'is_concierge',
            'is_usher',
            'user',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_editor',
            'is_concierge',
            'is_usher',
        },
    }

    project_id = immutable(
        db.Column(None, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    )
    project = immutable(
        db.relationship(
            Project,
            backref=db.backref(
                'crew_memberships', lazy='dynamic', cascade='all', passive_deletes=True
            ),
        )
    )
    parent = immutable(db.synonym('project'))
    parent_id = immutable(db.synonym('project_id'))

    # Project crew roles (at least one must be True):

    #: Editors can edit all common and editorial details of an event
    is_editor = db.Column(db.Boolean, nullable=False, default=False)
    #: Concierges are responsible for logistics and have write access
    #: to common details plus read access to everything else. Unlike
    #: editors, they cannot edit the schedule
    is_concierge = db.Column(db.Boolean, nullable=False, default=False)
    #: Ushers help participants find their way around an event and have
    #: the ability to scan badges at the door
    is_usher = db.Column(db.Boolean, nullable=False, default=False)

    @declared_attr
    def __table_args__(cls):
        args = list(super().__table_args__)
        args.append(
            db.CheckConstraint(
                db.or_(
                    cls.is_editor.is_(True),
                    cls.is_concierge.is_(True),
                    cls.is_usher.is_(True),
                ),
                name='project_crew_membership_has_role',
            )
        )
        return tuple(args)

    @cached_property
    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = set()
        if self.is_editor:
            roles.add('editor')
        if self.is_concierge:
            roles.add('concierge')
        if self.is_usher:
            roles.add('usher')
        roles.add('crew')
        roles.add('participant')
        return roles

    def roles_for(self, actor=None, anchors=()):
        roles = super(ProjectCrewMembership, self).roles_for(actor, anchors)
        if 'editor' in self.project.roles_for(actor, anchors):
            roles.add('project_editor')
        if 'admin' in self.project.profile.roles_for(actor, anchors):
            roles.add('profile_admin')
        return roles


# Project relationships: all crew, vs specific roles

Project.active_crew_memberships = with_roles(
    db.relationship(
        ProjectCrewMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            ProjectCrewMembership.project_id == Project.id,
            ProjectCrewMembership.is_active,
        ),
        viewonly=True,
    ),
    grants_via={'user': {'editor', 'concierge', 'usher', 'participant', 'crew'}},
)

Project.active_editor_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.project_id == Project.id,
        ProjectCrewMembership.is_active,
        ProjectCrewMembership.is_editor.is_(True),
    ),
    viewonly=True,
)

Project.active_concierge_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.project_id == Project.id,
        ProjectCrewMembership.is_active,
        ProjectCrewMembership.is_concierge.is_(True),
    ),
    viewonly=True,
)

Project.active_usher_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.project_id == Project.id,
        ProjectCrewMembership.is_active,
        ProjectCrewMembership.is_usher.is_(True),
    ),
    viewonly=True,
)

Project.crew = DynamicAssociationProxy('active_crew_memberships', 'user')
Project.editors = DynamicAssociationProxy('active_editor_memberships', 'user')
Project.concierges = DynamicAssociationProxy('active_concierge_memberships', 'user')
Project.ushers = DynamicAssociationProxy('active_usher_memberships', 'user')

# Similarly for users (add as needs come up)
User.projects_as_crew_active_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.user_id == User.id, ProjectCrewMembership.is_active
    ),
    viewonly=True,
)

User.projects_as_editor_active_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.user_id == User.id,
        ProjectCrewMembership.is_active,
        ProjectCrewMembership.is_editor.is_(True),
    ),
    viewonly=True,
)

User.projects_as_editor = DynamicAssociationProxy(
    'projects_as_editor_active_memberships', 'project'
)
