# -*- coding: utf-8 -*-

from flask.ext.lastuser.sqlalchemy import UserBase2, TeamBase
from . import db
from rsvp import RSVP

__all__ = ['User', 'Team']


# --- Models ------------------------------------------------------------------

class User(UserBase2, db.Model):
    __tablename__ = 'user'

    def rsvp_status(self, space_id):
      rsvp = RSVP.query.filter_by(proposal_space_id=space_id, user_id=self.id).first()
      if rsvp:
        return rsvp.rsvp_action
      else:
        return None


class Team(TeamBase, db.Model):
    __tablename__ = 'team'
