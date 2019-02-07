# -*- coding: utf-8 -*-

from flask import url_for
from coaster.sqlalchemy import add_primary_relationship
from . import db, BaseScopedNameMixin, MarkdownColumn, CoordinatesMixin, UuidMixin
from .project import Project


__all__ = ['Venue', 'VenueRoom']


class Venue(UuidMixin, BaseScopedNameMixin, CoordinatesMixin, db.Model):
    __tablename__ = 'venue'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project,
        backref=db.backref('venues', lazy='dynamic', cascade='all, delete-orphan', order_by='Venue.seq'))
    parent = db.synonym('project')
    description = MarkdownColumn('description', default=u'', nullable=False)
    address1 = db.Column(db.Unicode(160), default=u'', nullable=False)
    address2 = db.Column(db.Unicode(160), default=u'', nullable=False)
    city = db.Column(db.Unicode(30), default=u'', nullable=False)
    state = db.Column(db.Unicode(30), default=u'', nullable=False)
    postcode = db.Column(db.Unicode(20), default=u'', nullable=False)
    country = db.Column(db.Unicode(2), default=u'', nullable=False)

    seq = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)


class VenueRoom(BaseScopedNameMixin, db.Model):
    __tablename__ = 'venue_room'

    venue_id = db.Column(None, db.ForeignKey('venue.id'), nullable=False)
    venue = db.relationship(Venue,
        backref=db.backref('rooms', cascade='all, delete-orphan', order_by='VenueRoom.seq'))
    parent = db.synonym('venue')
    description = MarkdownColumn('description', default=u'', nullable=False)
    bgcolor = db.Column(db.Unicode(6), nullable=False, default=u'229922')

    seq = db.Column(db.Integer, nullable=False, default=0)

    scheduled_sessions = db.relationship("Session",
        primaryjoin='and_(Session.venue_room_id == VenueRoom.id, Session.scheduled)')

    __table_args__ = (db.UniqueConstraint('venue_id', 'name'),)

    @property
    def scoped_name(self):
        return u'{parent}/{name}'.format(parent=self.parent.name, name=self.name)


add_primary_relationship(Project, 'primary_venue', Venue, 'project', 'project_id')
