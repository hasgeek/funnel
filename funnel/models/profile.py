# -*- coding: utf-8 -*-

from flask_lastuser.sqlalchemy import ProfileBase

from . import MarkdownColumn, UuidMixin, db
from .user import UseridMixin, Team

__all__ = ['Profile']


class Profile(UseridMixin, UuidMixin, ProfileBase, db.Model):
    __tablename__ = 'profile'

    admin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    admin_team = db.relationship(Team)

    description = MarkdownColumn('description', default=u'', nullable=False)
    logo_url = db.Column(db.Unicode(2000), nullable=True)
    #: Legacy profiles are available via funnelapp, non-legacy in the main app
    legacy = db.Column(db.Boolean, default=False, nullable=False)

    teams = db.relationship(
        Team, primaryjoin='Profile.uuid == foreign(Team.org_uuid)',
        backref='profile', lazy='dynamic')

    __roles__ = {
        'all': {
            'read': {
                'id', 'name', 'title', 'description'
            },
        },
    }

    def permissions(self, user, inherited=None):
        perms = super(Profile, self).permissions(user, inherited)
        perms.add('view')
        if user:
            if (self.userid in user.user_organizations_owned_ids() or
                    (self.admin_team and user in self.admin_team.users)):
                perms.add('edit-profile')
                perms.add('new_project')
                perms.add('delete-project')
                perms.add('edit-project')
        return perms

    def roles_for(self, actor=None, anchors=()):
        roles = super(Profile, self).roles_for(actor, anchors)
        if actor is not None and self.admin_team in actor.teams:
            roles.add('admin')
        return roles
