# -*- coding: utf-8 -*-

from flask.ext.lastuser.sqlalchemy import UserBase
from . import db

__all__ = ['User']


# --- Models ------------------------------------------------------------------

class User(UserBase, db.Model):
    __tablename__ = 'user'
    description = db.Column(db.Text, default=u'', nullable=False)
