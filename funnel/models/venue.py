# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseNameMixin, BaseScopedNameMixin
from .space import ProposalSpace


__all__ = ['Venue', 'Room']


class Venue(BaseNameMixin, db.Model):
    __tablename__ = 'venue'

    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, backref=db.backref('venues', cascade='all, delete-orphan'))
    parent = db.synonym('proposal_space')
    description = db.Column(db.UnicodeText, default=u'', nullable=False)
    address1 = db.Column(db.Unicode(160), default=u'', nullable=False)
    address2 = db.Column(db.Unicode(160), default=u'', nullable=False)
    city = db.Column(db.Unicode(30), default=u'', nullable=False)
    state = db.Column(db.Unicode(30), default=u'', nullable=False)
    postcode = db.Column(db.Unicode(20), default=u'', nullable=False)
    country = db.Column(db.Unicode(2), default=u'', nullable=False)
    latitude = db.Column(db.Numeric(8, 5), nullable=True)
    longitude = db.Column(db.Numeric(8, 5), nullable=True)

    def url_for(self, action='new', _external=False):
        if action == 'new-room':
            return url_for('room_new', space=self.proposal_space.name, venue=self.name, _external=_external)
        elif action == 'delete':
            return url_for('venue_delete', space=self.proposal_space.name, venue=self.name, _external=_external)
        elif action == 'edit':
            return url_for('venue_edit', space=self.proposal_space.name, venue=self.name, _external=_external)


class Room(BaseScopedNameMixin, db.Model):
    __tablename__ = 'room'

    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    venue = db.relationship(Venue, backref=db.backref('rooms', cascade='all, delete-orphan'))
    parent = db.synonym('venue')
    description = db.Column(db.UnicodeText, default=u'', nullable=False)

    __table_args__ = (db.UniqueConstraint('name', 'venue_id'),)

    def url_for(self, action='new', _external=False):
        if action == 'delete':
            return url_for('room_delete', space=self.venue.proposal_space.name, venue=self.venue.name, room=self.name, _external=_external)
        elif action == 'edit':
            return url_for('room_edit', space=self.venue.proposal_space.name, venue=self.venue.name, room=self.name, _external=_external)
