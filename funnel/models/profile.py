# -*- coding: utf-8 -*-

from flask import url_for
from flask.ext.lastuser.sqlalchemy import ProfileBase
from . import db, MarkdownColumn

__all__ = ['Profile']


class Profile(ProfileBase, db.Model):
    __tablename__ = 'profile'

    description = MarkdownColumn('description', default=u'', nullable=False)

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('profile_view', profile=self.name, _external=_external)
        elif action == 'new-space':
            return url_for('proposalspace_new', profile=self.name, _external=_external)
