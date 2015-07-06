# -*- coding: utf-8 -*-

from . import db, BaseMixin

__all__ = ['ContactExchange']


class ContactExchange(BaseMixin, db.Model):
    """
    Model to track who scanned whose badge, at which event.
    """
    __tablename__ = 'contact_exchange'
    user_id = db.Column(None, db.ForeignKey('user.id'))
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'))
    participant_id = db.Column(None, db.ForeignKey('participant.id'))
    __table_args__ = (db.UniqueConstraint('user_id', 'proposal_space_id', 'participant_id'),)
