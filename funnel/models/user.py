# -*- coding: utf-8 -*-

from flask.ext.lastuser.sqlalchemy import UserBase2
from . import db

__all__ = ['User']


# --- Models ------------------------------------------------------------------

class User(UserBase2, db.Model):
    __tablename__ = 'user'
    description = db.Column(db.Text, default=u'', nullable=False)
