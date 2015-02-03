# -*- coding: utf-8 -*-

from . import db, TimestampMixin
from coaster.utils import LabeledEnum
from baseframe import __
from .space import ProposalSpace
from .user import User

__all__ = ['Rsvp', 'RSVP_ACTION']


class RSVP_ACTION(LabeledEnum):
    RSVP_Y = ('Y', {'label': __("I'm going"), 'category': 'success'})
    RSVP_N = ('N', {'label': __("Not going"), 'category': 'danger'})
    RSVP_M = ('M', {'label': __("Maybe"), 'category': 'default'})
    # RSVP_A = ('A', {'label': __("Awaiting"), 'category': 'default', 'order': 4, 'active': False})
    __order__ = (RSVP_Y, RSVP_N, RSVP_M)


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
    def rsvp_actions(cls, space):
        # A new list is being generated with the responses count appended
        def append_rsvp_responses_count(action):
            action[1]['responses_count'] = cls.query.filter_by(proposal_space=space, rsvp_action=action[0]).count()
            return action
        return map(append_rsvp_responses_count, RSVP_ACTION.items())

    @classmethod
    def get_for(cls, space, user):
        return cls.query.filter_by(proposal_space_id=space.id, user_id=user.id).first()
