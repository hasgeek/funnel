# -*- coding: utf-8 -*-

from flask import url_for
from . import db, UuidMixin, BaseScopedIdNameMixin, MarkdownColumn
from .space import ProposalSpace
from .proposal import Proposal
from .venue import VenueRoom


__all__ = ['Session']


class Session(UuidMixin, BaseScopedIdNameMixin, db.Model):
    __tablename__ = 'session'

    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('sessions', cascade='all, delete-orphan'))
    parent = db.synonym('proposal_space')
    description = MarkdownColumn('description', default=u'', nullable=False)
    speaker_bio = MarkdownColumn('speaker_bio', default=u'', nullable=False)
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), nullable=True, unique=True)
    proposal = db.relationship(Proposal,
        backref=db.backref('session', uselist=False, cascade='all, delete-orphan'))
    speaker = db.Column(db.Unicode(200), default=None, nullable=True)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    venue_room_id = db.Column(db.Integer, db.ForeignKey('venue_room.id'), nullable=True)
    venue_room = db.relationship(VenueRoom, backref=db.backref('sessions'))
    is_break = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'url_id'),)

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return self.proposal_space.url_for('schedule', _external=_external) + u'#' + self.url_name
        elif action == 'edit':
            return url_for('session_edit', profile=self.proposal_space.profile.name, space=self.proposal_space.name, session=self.url_name, _external=_external)
        elif action == 'delete':
            return url_for('session_delete', profile=self.proposal_space.profile.name, space=self.proposal_space.name, session=self.url_name, _external=_external)
        elif action == 'feedback':
            return url_for('session_feedback', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.proposal.url_name, _external=_external)
        elif action == 'view-popup':
            return url_for('session_view_popup', profile=self.proposal_space.profile.name, space=self.proposal_space.name, session=self.url_name, _external=_external)
