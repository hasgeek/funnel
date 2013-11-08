# -*- coding: utf-8 -*-

from datetime import datetime
from . import db, BaseScopedNameMixin, MarkdownColumn


__all__ = ['Schedule']


class Schedule(BaseScopedNameMixin, db.Model):
    __tablename__ = 'schedule'

    description = MarkdownColumn('description', default=u'', nullable=False)
    proposal_id = db.Column(db.Integer, nullable=True)
    start_datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    time_zone = db.Column(db.Unicode(30), default=u'UTC', nullable=False)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    venue_room_id = db.Column(db.Integer, db.ForeignKey('venue_room.id'), nullable=False)
    is_break = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint('name', 'start_datetime', 'end_datetime'),)
