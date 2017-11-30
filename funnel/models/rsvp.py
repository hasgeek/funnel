# -*- coding: utf-8 -*-

from coaster.utils import LabeledEnum
from coaster.sqlalchemy import StateManager
from baseframe import __
from . import db, TimestampMixin
from .space import ProposalSpace
from .user import User

__all__ = ['Rsvp', 'RSVP_STATUS']


class RSVP_STATUS(LabeledEnum):
    Y = ('Y', 'yes', __("Yes"))
    N = ('N', 'no', __("No"))
    M = ('M', 'maybe', __("Maybe"))
    A = ('A', 'awaiting', __("Awaiting"))
    # To avoid interfering with LabeledEnum, the following should use a list, not a tuple,
    # and should contain actual status values, not Python objects
    USER_CHOICES = ['Y', 'N', 'M']


class Rsvp(TimestampMixin, db.Model):
    __tablename__ = 'rsvp'
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('rsvps', cascade='all, delete-orphan', lazy='dynamic'))
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    user = db.relationship(User)

    _state = db.Column('status', db.CHAR(1), StateManager.check_constraint('status', RSVP_STATUS),
        default=RSVP_STATUS.A, nullable=False)
    state = StateManager('_state', RSVP_STATUS, doc="RSVP answer")

    @classmethod
    def get_for(cls, space, user, create=False):
        if user:
            result = cls.query.get((space.id, user.id))
            if not result and create:
                result = cls(proposal_space=space, user=user)
                db.session.add(result)
            return result


def _space_rsvp_for(self, user, create=False):
    return Rsvp.get_for(self, user, create)


def _space_rsvps_with(self, status):
    return self.rsvps.filter_by(_state=status)


def _space_rsvp_counts(self):
    return dict(db.session.query(Rsvp._state, db.func.count(Rsvp._state)).filter(
        Rsvp.proposal_space == self).group_by(Rsvp._state).all())


ProposalSpace.rsvp_for = _space_rsvp_for
ProposalSpace.rsvps_with = _space_rsvps_with
ProposalSpace.rsvp_counts = _space_rsvp_counts
