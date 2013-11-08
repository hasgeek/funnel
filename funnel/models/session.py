# -*- coding: utf-8 -*-

from datetime import datetime
from . import db, BaseScopedIdMixin, MarkdownColumn


__all__ = ['Session']


class Session(BaseScopedIdMixin, db.Model):
    __tablename__ = 'session'

    description = MarkdownColumn('description', default=u'', nullable=False)
    proposal_id = db.Column(db.Integer, nullable=True)
    start_datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    proposal_space_id = db.Column(db.Integer, 
    	backref=db.backref('sessions', cascade='all, delete-orphan', order_by='Session.start_datetime'),
    	nullable=False)
    venue_room_id = db.Column(db.Integer, db.ForeignKey('venue_room.id'), nullable=False)
    is_break = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint('name', 'start_datetime', 'end_datetime'),)
