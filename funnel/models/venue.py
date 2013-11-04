# -*- coding: utf-8 -*-

from . import db, BaseNameMixin, BaseScopedNameMixin
from .space import ProposalSpace


__all__ = ['Venue', 'Room']


class Venue(BaseNameMixin, db.Model):
    __tablename__ = 'venue'

    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace)
    description = db.Column(db.UnicodeText, default=u'', nullable=False)
    address1 = db.Column(db.Unicode(80), default=u'', nullable=False)
    address2 = db.Column(db.Unicode(80), default=u'', nullable=False)
    city = db.Column(db.Unicode(30), default=u'', nullable=False)
    state = db.Column(db.Unicode(30), default=u'', nullable=False)
    postcode = db.Column(db.Unicode(20), default=u'', nullable=False)
    country = db.Column(db.Unicode(2), default=u'', nullable=False)
    latitude = db.Column(db.Numeric(8, 5), nullable=True)
    longitude = db.Column(db.Numeric(8, 5), nullable=True)


class Room(BaseScopedNameMixin, db.Model):
    __tablename__ = 'room'

    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    venue = db.relationship(Venue)
    description = db.Column(db.UnicodeText, default=u'', nullable=False)
