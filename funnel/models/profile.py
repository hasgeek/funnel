# -*- coding: utf-8 -*-

from flask_lastuser.sqlalchemy import ProfileBase

from . import MarkdownColumn, TSVectorType, UrlType, UuidMixin, db
from .helpers import RESERVED_NAMES, add_search_trigger
from .user import Team, UseridMixin

__all__ = ['Profile']


class Profile(UseridMixin, UuidMixin, ProfileBase, db.Model):
    __tablename__ = 'profile'
    reserved_names = RESERVED_NAMES

    admin_team_id = db.Column(
        None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True
    )
    admin_team = db.relationship(Team)

    description = MarkdownColumn('description', default=u'', nullable=False)
    logo_url = db.Column(UrlType, nullable=True)
    #: Legacy profiles are available via funnelapp, non-legacy in the main app
    legacy = db.Column(db.Boolean, default=False, nullable=False)

    search_vector = db.deferred(
        db.Column(
            TSVectorType(
                'name',
                'title',
                'description_text',
                weights={'name': 'A', 'title': 'A', 'description_text': 'B'},
                regconfig='english',
                hltext=lambda: db.func.concat_ws(
                    ' / ', Profile.title, Profile.description_html
                ),
            ),
            nullable=False,
        )
    )

    teams = db.relationship(
        Team,
        primaryjoin='Profile.uuid == foreign(Team.org_uuid)',
        backref='profile',
        lazy='dynamic',
    )

    __table_args__ = (
        db.Index('ix_profile_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __roles__ = {'all': {'read': {'id', 'name', 'title', 'description'}}}

    def permissions(self, user, inherited=None):
        perms = super(Profile, self).permissions(user, inherited)
        perms.add('view')
        if user:
            if self.userid in user.user_organizations_owned_ids() or (
                self.admin_team and user in self.admin_team.users
            ):
                perms.add('edit-profile')
                perms.add('new_project')
                perms.add('delete-project')
                perms.add('edit_project')
        return perms

    def roles_for(self, actor=None, anchors=()):
        roles = super(Profile, self).roles_for(actor, anchors)

        # TODO: Remove this admin test when the Team model is removed as part of the
        # migration to memberships
        if actor is not None and self.admin_team in actor.teams:
            roles.add('admin')
            roles.add('profile_admin')

        membership = self.active_admin_memberships.filter_by(user=actor).one_or_none()
        if membership:
            roles.update(membership.offered_roles())

        return roles


add_search_trigger(Profile, 'search_vector')
