# -*- coding: utf-8 -*-

from flask import url_for
from flask_lastuser.sqlalchemy import ProfileBase
from . import db, MarkdownColumn
from .user import Team

__all__ = ['Profile']


class Profile(ProfileBase, db.Model):
    __tablename__ = 'profile'

    admin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    admin_team = db.relationship(Team)

    description = MarkdownColumn('description', default=u'', nullable=False)

    def permissions(self, user, inherited=None):
        perms = super(Profile, self).permissions(user, inherited)
        perms.add('view')
        if user:
            if (self.userid in user.user_organizations_owned_ids()
                    or (self.admin_team and user in self.admin_team.users)):
                perms.add('edit-profile')
                perms.add('new-space')
                perms.add('delete-space')
                perms.add('edit-space')
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('profile_view', profile=self.name, _external=_external)
        if action == 'edit':
            return url_for('profile_edit', profile=self.name, _external=_external)
        elif action == 'new-space':
            return url_for('space_new', profile=self.name, _external=_external)

    def roles_for(self, actor=None, anchors=()):
        roles = super(Profile, self).roles_for(actor, anchors)
        if actor is not None and self.admin_team in actor.teams:
            roles.add('admin')
        return roles
