# -*- coding: utf-8 -*-

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.orderinglist import ordering_list

from coaster.sqlalchemy import add_primary_relationship, with_roles

from . import BaseScopedNameMixin, CoordinatesMixin, MarkdownColumn, UuidMixin, db
from .project import Project

__all__ = ['Venue', 'VenueRoom']


class Venue(UuidMixin, BaseScopedNameMixin, CoordinatesMixin, db.Model):
    __tablename__ = 'venue'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project)
    parent = db.synonym('project')
    description = MarkdownColumn('description', default='', nullable=False)
    address1 = db.Column(db.Unicode(160), default='', nullable=False)
    address2 = db.Column(db.Unicode(160), default='', nullable=False)
    city = db.Column(db.Unicode(30), default='', nullable=False)
    state = db.Column(db.Unicode(30), default='', nullable=False)
    postcode = db.Column(db.Unicode(20), default='', nullable=False)
    country = db.Column(db.Unicode(2), default='', nullable=False)

    rooms = db.relationship(
        'VenueRoom',
        cascade='all, delete-orphan',
        order_by='VenueRoom.seq',
        collection_class=ordering_list('seq', count_from=1),
    )

    seq = db.Column(db.Integer, nullable=False)

    project_editors = with_roles(
        association_proxy('project', 'editors'), grants={'project_editor'}
    )
    project_concierges = with_roles(
        association_proxy('project', 'concierges'), grants={'project_concierge'}
    )
    project_ushers = with_roles(
        association_proxy('project', 'ushers'), grants={'project_usher'}
    )

    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'id',
                'name',
                'title',
                'description',
                'address1',
                'address2',
                'city',
                'state',
                'postcode',
                'country',
                'project_details',
                'room_list',
                'seq',
                'suuid',
                'latitude',
                'longitude',
                'has_coordinates',
            }
        }
    }

    @property
    def project_details(self):
        return {
            'name': self.project.name,
            'title': self.project.title,
            'suuid': self.project.suuid,
        }

    @property
    def room_list(self):
        return [room.current_access() for room in self.rooms]


class VenueRoom(UuidMixin, BaseScopedNameMixin, db.Model):
    __tablename__ = 'venue_room'

    venue_id = db.Column(None, db.ForeignKey('venue.id'), nullable=False)
    venue = db.relationship(Venue)
    parent = db.synonym('venue')
    description = MarkdownColumn('description', default='', nullable=False)
    bgcolor = db.Column(db.Unicode(6), nullable=False, default='229922')

    seq = db.Column(db.Integer, nullable=False)

    scheduled_sessions = db.relationship(
        "Session",
        primaryjoin='and_(Session.venue_room_id == VenueRoom.id, Session.scheduled)',
    )

    project_editors = with_roles(
        association_proxy('venue', 'project_editors'), grants={'project_editor'}
    )
    project_concierges = with_roles(
        association_proxy('venue', 'project_concierges'), grants={'project_concierge'}
    )
    project_ushers = with_roles(
        association_proxy('venue', 'project_ushers'), grants={'project_usher'}
    )

    __table_args__ = (db.UniqueConstraint('venue_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'id',
                'name',
                'title',
                'description',
                'bgcolor',
                'seq',
                'venue_details',
                'scoped_name',
                'suuid',
            }
        }
    }

    @property
    def venue_details(self):
        return {
            'name': self.venue.name,
            'title': self.venue.title,
            'suuid': self.venue.suuid,
        }

    @property
    def scoped_name(self):
        return '{parent}/{name}'.format(parent=self.parent.name, name=self.name)


add_primary_relationship(Project, 'primary_venue', Venue, 'project', 'project_id')
