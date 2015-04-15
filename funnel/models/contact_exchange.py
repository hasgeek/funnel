# -*- coding: utf-8 -*-

from . import db, BaseMixin

__all__ = ['ContactExchange']


class ContactExchange(BaseMixin, db.Model):
    __tablename__ = 'contact_exchange'
    user_id = db.Column(None, db.ForeignKey('user.id'), primary_key=True)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), primary_key=True)
    participant_id = db.Column(None, db.ForeignKey('participant.id'), primary_key=True)
