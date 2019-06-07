# -*- coding: utf-8 -*-

from flask_lastuser.sqlalchemy import ProfileBase

from . import MarkdownColumn, UuidMixin, UrlType, TSVectorType, db
from .user import UseridMixin, Team
from .helper import RESERVED_NAMES, SearchQuery

__all__ = ['Profile']


class Profile(UseridMixin, UuidMixin, ProfileBase, db.Model):
    __tablename__ = 'profile'
    query_class = SearchQuery
    reserved_names = RESERVED_NAMES

    admin_team_id = db.Column(None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True)
    admin_team = db.relationship(Team)

    description = MarkdownColumn('description', default=u'', nullable=False)
    logo_url = db.Column(UrlType, nullable=True)
    #: Legacy profiles are available via funnelapp, non-legacy in the main app
    legacy = db.Column(db.Boolean, default=False, nullable=False)

    search_vector = db.Column(TSVectorType(
        'name', 'title', 'description',
        weights={'name': 'A', 'title': 'A', 'description': 'B'}
        ))

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
            if (self.userid in user.user_organizations_owned_ids()
                    or (self.admin_team and user in self.admin_team.users)):
                perms.add('edit-profile')
                perms.add('new_project')
                perms.add('delete-project')
                perms.add('edit_project')
        return perms

    def roles_for(self, actor=None, anchors=()):
        roles = super(Profile, self).roles_for(actor, anchors)
        if actor is not None and self.admin_team in actor.teams:
            roles.add('admin')
        return roles
