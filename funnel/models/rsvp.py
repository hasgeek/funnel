# -*- coding: utf-8 -*-

from . import db, TimestampMixin
from coaster.utils import LabeledEnum
from baseframe import __
from .space import ProposalSpace
from .user import User

__all__ = ['Rsvp']


class RSVP_ACTION(LabeledEnum):
    RSVP_Y = ('Y', {'label': __("I'm going"), 'category': 'success', 'order': 1, 'active': True})
    RSVP_N = ('N', {'label': __("Not going"), 'category': 'danger', 'order': 2, 'active': True})
    RSVP_M = ('M', {'label': __("Maybe"), 'category': 'default', 'order': 3, 'active': True})
    RSVP_A = ('A', {'label': __("Awaiting"), 'category': 'default', 'order': 4, 'active': False})


class Rsvp(TimestampMixin, db.Model):
    __tablename__ = 'rsvp'
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id)
    user = db.relationship(User, primaryjoin=user_id == User.id)

    rsvp_action = db.Column(db.Enum(*RSVP_ACTION.keys(), name='rsvp_action'), default=RSVP_ACTION, nullable=False)

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'user_id'),)

    def __init__(self, **kwargs):
        super(Rsvp, self).__init__(**kwargs)

    @classmethod
    def rsvp_actions(self, space):
        # A new list is being generated with the responses count appended
        def append_rsvp_responses_count(action):
            action[1]['responses_count'] = Rsvp.query.filter_by(proposal_space=space, rsvp_action=action[0]).count()
            return action
        return map(append_rsvp_responses_count,
                   sorted((item for item in RSVP_ACTION.items() if item[1]['active']), key=lambda action: action[1]['order']))

    @classmethod
    def user_rsvp_status(self, space, user):
        if user:
            rsvp = Rsvp.query.get((space.id, user.id))
            return rsvp.rsvp_action if rsvp else None

