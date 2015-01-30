# -*- coding: utf-8 -*-

from . import db, TimestampMixin
from coaster.utils import LabeledEnum
from baseframe import __

__all__ = ['RSVP', 'RSVP_ACTION', 'RSVPMixin']


class RSVP_ACTION(LabeledEnum):
    RSVP_Y = ('Y', {'label': "I'm going", 'category': 'success', 'order': 1})
    RSVP_N = ('N', {'label': 'Not going', 'category': 'danger', 'order': 2})
    RSVP_M = ('M', {'label': 'Maybe', 'category': 'default', 'order': 3})


class RSVP(TimestampMixin, db.Model):
    __tablename__ = 'rsvp'
    __table_args__ = (db.UniqueConstraint('user_id', 'proposal_space_id'),)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    rsvp_action = db.Column(db.Enum(*RSVP_ACTION.keys(), name='rsvp_action'), default=RSVP_ACTION)

    def __init__(self, **kwargs):
        super(RSVP, self).__init__(**kwargs)

class RSVPMixin(object):

    allow_rsvp = db.Column(db.Boolean, default=False)

    def rsvp_actions(self):
        if self.allow_rsvp:
            return sorted(RSVP_ACTION.items(), key=lambda action: action[1]['order'])
        else:
            return []

    def rsvp_responses_count(self, action):
        return RSVP.query.filter_by(proposal_space_id=self.id, rsvp_action=action).count()

    def user_rsvp_status(self, user_id):
        rsvp = RSVP.query.filter_by(proposal_space_id=self.id, user_id=user_id).first()
        if rsvp:
            return rsvp.rsvp_action
        else:
            return None
