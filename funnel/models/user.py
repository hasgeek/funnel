# -*- coding: utf-8 -*-

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import UUIDType

from coaster.sqlalchemy import SqlBuidComparator
from coaster.utils import buid2uuid, uuid2buid
from flask_lastuser.sqlalchemy import TeamBase, UserBase2

from . import UuidMixin, db

__all__ = ['User', 'Team']

# --- Mixins ------------------------------------------------------------------


# This overrides the `userid` column inherited from Flask-Lastuser. We've
# switched to UUIDs in Funnel.
class UseridMixin(object):
    @hybrid_property
    def userid(self):
        return uuid2buid(self.uuid)

    @userid.setter
    def userid(self, value):
        self.uuid = buid2uuid(value)

    @userid.comparator
    def userid(cls):
        return SqlBuidComparator(cls.uuid)


# --- Models ------------------------------------------------------------------

class User(UseridMixin, UuidMixin, UserBase2, db.Model):
    __tablename__ = 'user'

    __roles__ = {
        'all': {
            'read': {
                'username', 'fullname', 'avatar',
                }
            },
        'owner': {
            'read': {
                'email', 'phone', 'profile_url',
                }
            }
        }

    def roles_for(self, actor, anchors=()):
        roles = super(User, self).roles_for(actor, anchors)
        if actor == self:
            roles.add('owner')
        return roles


class Team(UseridMixin, UuidMixin, TeamBase, db.Model):
    __tablename__ = 'team'

    # TODO: This should be a foreign key to Profile.uuid, but since
    # we collect all teams from user accounts without the corresponding
    # profiles (profile autogeneration is disabled), the foreign key can
    # be added only when the autogeneration policy changes.
    org_uuid = db.Column(UUIDType(binary=False), index=True, nullable=False)

    # This overrides the `orgid` column from Flask-Lastuser. We've switched to
    # UUIDs but need this to exist for the sake of code in Flask-Lastuser.
    @hybrid_property
    def orgid(self):
        return uuid2buid(self.org_uuid)

    @orgid.setter
    def orgid(self, value):
        self.org_uuid = buid2uuid(value)

    @orgid.comparator
    def orgid(cls):
        return SqlBuidComparator(cls.org_uuid)

    def __repr__(self):
        return '<Team %r of %r>' % (self.title, self.profile.title if self.profile else '(missing)')
