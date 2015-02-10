# -*- coding: utf-8 -*-

from . import db, TimestampMixin
from coaster.utils import LabeledEnum
from baseframe import __
from .space import ProposalSpace
from .user import User

__all__ = ['Rsvp', 'RSVP_STATUS']


class RSVP_STATUS(LabeledEnum):
    Y = ('Y', __("Yes"))
    N = ('N', __("No"))
    M = ('M', __("Maybe"))
    A = ('A', __("Awaiting"))
    __order__ = (Y, N, M, A)


class Rsvp(TimestampMixin, db.Model):
    __tablename__ = 'rsvp'
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('rsvps', cascade='all, delete-orphan', lazy='dynamic'))
    user = db.relationship(User)

    status = db.Column(db.Enum(*RSVP_STATUS.keys(), name='rsvp_status_enum'), default=RSVP_STATUS.A, nullable=False)

    @classmethod
    def get_for(cls, space, user, create=False):
        if user:
            result = cls.query.get((space.id, user.id))
            if not result and create:
                result = cls(proposal_space=space, user=user)
                db.session.add(result)
            return result
