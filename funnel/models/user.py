# -*- coding: utf-8 -*-

from flask_lastuser.sqlalchemy import TeamBase, UserBase2

from . import UuidMixin, db

__all__ = ['User', 'Team']


# --- Models ------------------------------------------------------------------

class User(UuidMixin, UserBase2, db.Model):
    __tablename__ = 'user'

    userid = UuidMixin.buid


class Team(UuidMixin, TeamBase, db.Model):
    __tablename__ = 'team'

    userid = UuidMixin.buid
