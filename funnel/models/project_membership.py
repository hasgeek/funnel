# -*- coding: utf-8 -*-

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr

from coaster.sqlalchemy import immutable, with_roles

from . import db
from .membership import ImmutableMembershipMixin
from .project import Project
from .user import User

__all__ = ['ProjectCrewMembership']


class ProjectCrewMembership(ImmutableMembershipMixin, db.Model):
    """
    Users can be crew members of projects, with specified access rights.
    """

    __tablename__ = 'project_crew_membership'

    # List of is_role columns in this model
    __data_columns__ = ('is_editor', 'is_concierge', 'is_usher')
    __parent_column__ = 'project_id'

    __roles__ = {
        'all': {
            'read': {
                'user_details',
                'is_editor',
                'is_concierge',
                'is_usher',
                'project',
            },
            'call': {'url_for'},
        },
        'editor': {'read': {'edit_url', 'delete_url'}},
    }

    project_id = immutable(
        db.Column(None, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    )
    project = immutable(
        db.relationship(
            Project,
            backref=db.backref(
                'crew_memberships',
                lazy='dynamic',
                cascade='all, delete-orphan',
                passive_deletes=True,
            ),
        )
    )
    parent = immutable(db.synonym('project'))

    user_id = immutable(
        db.Column(
            None,
            db.ForeignKey('user.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        )
    )
    user = with_roles(
        immutable(
            db.relationship(
                User,
                foreign_keys=[user_id],
                backref=db.backref(
                    'profile_crew_memberships',
                    lazy='dynamic',
                    cascade='all, delete-orphan',
                    passive_deletes=True,
                ),
            )
        ),
        grants={'subject'},
    )

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
        args = list(super(cls, cls).__table_args__)
        args.append(
            db.CheckConstraint(
                'is_editor IS TRUE OR is_concierge IS TRUE OR is_usher IS TRUE',
                name='project_crew_membership_has_role',
            )
        )
        return tuple(args)

    @property
    def user_details(self):
        return {
            'fullname': self.user.fullname,
            'username': self.user.username,
            'avatar': self.user.avatar,
        }

    @property
    def edit_url(self):
        return self.url_for('edit', _external=True)

    @property
    def delete_url(self):
        return self.url_for('delete', _external=True)

    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = set()
        if self.is_editor:
            roles.add('project_editor')
        if self.is_concierge:
            roles.add('project_concierge')
        if self.is_usher:
            roles.add('project_usher')
        return roles

    def roles_for(self, actor, anchors=()):
        """Roles available to the specified actor and anchors"""
        roles = super(ProjectCrewMembership, self).roles_for(actor, anchors)
        if 'profile_admin' in self.project.profile.roles_for(actor, anchors):
            roles.add('editor')
        return roles


# Project relationships: all crew, vs specific roles

Project.active_crew_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.project_id == Project.id,
        ProjectCrewMembership.active,
        ~ProjectCrewMembership.is_invite,
    ),
)

Project.active_editor_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.project_id == Project.id,
        ProjectCrewMembership.active,
        ProjectCrewMembership.is_editor.is_(True),
        ~ProjectCrewMembership.is_invite,
    ),
)

Project.active_concierge_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.project_id == Project.id,
        ProjectCrewMembership.active,
        ProjectCrewMembership.is_concierge.is_(True),
        ~ProjectCrewMembership.is_invite,
    ),
)

Project.active_usher_memberships = db.relationship(
    ProjectCrewMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProjectCrewMembership.project_id == Project.id,
        ProjectCrewMembership.active,
        ProjectCrewMembership.is_usher.is_(True),
        ~ProjectCrewMembership.is_invite,
    ),
)

Project.crew = association_proxy('active_crew_memberships', 'user')
Project.editors = association_proxy('active_editor_memberships', 'user')
Project.concierges = association_proxy('active_concierge_memberships', 'user')
Project.ushers = association_proxy('active_usher_memberships', 'user')
