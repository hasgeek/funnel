# -*- coding: utf-8 -*-

from flask.ext.lastuser.sqlalchemy import UserBase2, TeamBase
from . import db
from rsvp import RSVP

__all__ = ['User', 'Team']


# --- Models ------------------------------------------------------------------

class User(UserBase2, db.Model):
    __tablename__ = 'user'


class Team(TeamBase, db.Model):
    __tablename__ = 'team'
