# -*- coding: utf-8 -*-

from . import db, TimestampMixin
from .user import User
from .event import Participant

__all__ = ['ContactExchange']


class ContactExchange(TimestampMixin, db.Model):
    """
    Model to track who scanned whose badge, at which event.
    """
    __tablename__ = 'contact_exchange'
    user_id = db.Column(None, db.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True)
    user = db.relationship(User,
        backref=db.backref('scanned_contacts', lazy='dynamic', passive_deletes=True))
    participant_id = db.Column(None, db.ForeignKey('participant.id', ondelete='CASCADE'),
        primary_key=True, index=True)
    participant = db.relationship(Participant,
        backref=db.backref('scanned_contacts', passive_deletes=True))
