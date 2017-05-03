# -*- coding: utf-8 -*-

from flask_lastuser.sqlalchemy import UserBase2, TeamBase
from . import db

__all__ = ['User', 'Team']


# --- Models ------------------------------------------------------------------

class User(UserBase2, db.Model):
    __tablename__ = 'user'


class Team(TeamBase, db.Model):
    __tablename__ = 'team'
