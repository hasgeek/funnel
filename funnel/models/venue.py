# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseScopedNameMixin, MarkdownColumn, CoordinatesMixin
from .project import Project


__all__ = ['Venue', 'VenueRoom']


class Venue(BaseScopedNameMixin, CoordinatesMixin, db.Model):
    __tablename__ = 'venue'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project,
        backref=db.backref('venues', cascade='all, delete-orphan', order_by='Venue.name'))
    parent = db.synonym('project')
    description = MarkdownColumn('description', default=u'', nullable=False)
    address1 = db.Column(db.Unicode(160), default=u'', nullable=False)
    address2 = db.Column(db.Unicode(160), default=u'', nullable=False)
    city = db.Column(db.Unicode(30), default=u'', nullable=False)
    state = db.Column(db.Unicode(30), default=u'', nullable=False)
    postcode = db.Column(db.Unicode(20), default=u'', nullable=False)
    country = db.Column(db.Unicode(2), default=u'', nullable=False)

    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)

    def url_for(self, action='new', _external=False):
        if action == 'new-room':
            return url_for('venueroom_new', profile=self.project.profile.name, project=self.project.name, venue=self.name, _external=_external)
        elif action == 'delete':
            return url_for('venue_delete', profile=self.project.profile.name, project=self.project.name, venue=self.name, _external=_external)
        elif action == 'edit':
            return url_for('venue_edit', profile=self.project.profile.name, project=self.project.name, venue=self.name, _external=_external)


class VenueRoom(BaseScopedNameMixin, db.Model):
    __tablename__ = 'venue_room'

    venue_id = db.Column(None, db.ForeignKey('venue.id'), nullable=False)
    venue = db.relationship(Venue,
        backref=db.backref('rooms', cascade='all, delete-orphan', order_by='VenueRoom.name'))
    parent = db.synonym('venue')
    description = MarkdownColumn('description', default=u'', nullable=False)
    bgcolor = db.Column(db.Unicode(6), nullable=False, default=u'229922')

    __table_args__ = (db.UniqueConstraint('venue_id', 'name'),)

    @property
    def scoped_name(self):
        return u'{parent}/{name}'.format(parent=self.parent.name, name=self.name)

    def url_for(self, action='new', _external=False):
        if action == 'delete':
            return url_for('venueroom_delete', profile=self.venue.project.profile.name, project=self.venue.project.name, venue=self.venue.name, room=self.name, _external=_external)
        if action == 'ical-schedule':
            return url_for('schedule_room_ical', profile=self.venue.project.profile.name, project=self.venue.project.name, venue=self.venue.name, room=self.name, _external=_external).replace('https', 'webcal').replace('http', 'webcal')
        elif action == 'edit':
            return url_for('venueroom_edit', profile=self.venue.project.profile.name, project=self.venue.project.name, venue=self.venue.name, room=self.name, _external=_external)
