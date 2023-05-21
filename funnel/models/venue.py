"""Model for project venue and rooms within a venue (legacy, pending global venues)."""

from __future__ import annotations

from typing import List
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import
import itertools

from sqlalchemy.ext.orderinglist import ordering_list

from coaster.sqlalchemy import add_primary_relationship, with_roles

from . import (
    BaseScopedNameMixin,
    CoordinatesMixin,
    Mapped,
    MarkdownCompositeBasic,
    UuidMixin,
    db,
    sa,
)
from .helpers import reopen
from .project import Project
from .project_membership import project_child_role_map

__all__ = ['Venue', 'VenueRoom']


class Venue(
    UuidMixin,
    BaseScopedNameMixin,
    CoordinatesMixin,
    db.Model,  # type: ignore[name-defined]
):
    __tablename__ = 'venue'
    __allow_unmapped__ = True

    project_id = sa.Column(sa.Integer, sa.ForeignKey('project.id'), nullable=False)
    project: Mapped[Project] = with_roles(
        sa.orm.relationship(Project, back_populates='venues'),
        grants_via={None: project_child_role_map},
    )
    parent: Mapped[Project] = sa.orm.synonym('project')
    description = MarkdownCompositeBasic.create(
        'description', default='', nullable=False
    )
    address1 = sa.Column(sa.Unicode(160), default='', nullable=False)
    address2 = sa.Column(sa.Unicode(160), default='', nullable=False)
    city = sa.Column(sa.Unicode(30), default='', nullable=False)
    state = sa.Column(sa.Unicode(30), default='', nullable=False)
    postcode = sa.Column(sa.Unicode(20), default='', nullable=False)
    country = sa.Column(sa.Unicode(2), default='', nullable=False)

    rooms: Mapped[List[VenueRoom]] = sa.orm.relationship(
        'VenueRoom',
        cascade='all',
        order_by='VenueRoom.seq',
        collection_class=ordering_list('seq', count_from=1),
        back_populates='venue',
    )

    seq = sa.Column(sa.Integer, nullable=False)

    __table_args__ = (sa.UniqueConstraint('project_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'name',
                'title',
                'description',
                'address1',
                'address2',
                'city',
                'state',
                'postcode',
                'country',
                'rooms',
                'seq',
                'uuid_b58',
                'latitude',
                'longitude',
                'has_coordinates',
                'coordinates',
                'project',
            }
        }
    }

    __datasets__ = {
        'without_parent': {
            'name',
            'title',
            'description',
            'address1',
            'address2',
            'city',
            'state',
            'postcode',
            'country',
            'rooms',
            'seq',
            'uuid_b58',
            'latitude',
            'longitude',
            'has_coordinates',
            'coordinates',
        },
        'related': {'name', 'title', 'uuid_b58'},
    }


class VenueRoom(UuidMixin, BaseScopedNameMixin, db.Model):  # type: ignore[name-defined]
    __tablename__ = 'venue_room'
    __allow_unmapped__ = True

    venue_id = sa.Column(sa.Integer, sa.ForeignKey('venue.id'), nullable=False)
    venue: Mapped[Venue] = with_roles(
        sa.orm.relationship(Venue, back_populates='rooms'),
        # Since Venue already remaps Project roles, we just want the remapped role names
        grants_via={None: set(itertools.chain(*project_child_role_map.values()))},
    )
    parent: Mapped[Venue] = sa.orm.synonym('venue')
    description = MarkdownCompositeBasic.create(
        'description', default='', nullable=False
    )
    bgcolor = sa.Column(sa.Unicode(6), nullable=False, default='229922')

    seq = sa.Column(sa.Integer, nullable=False)

    __table_args__ = (sa.UniqueConstraint('venue_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                # TODO: id is used in SessionForm.venue_room_id; needs to be .venue_room
                'id',
                'name',
                'title',
                'description',
                'bgcolor',
                'seq',
                'venue',
                'scoped_name',
                'uuid_b58',
            }
        }
    }

    __datasets__ = {
        'without_parent': {
            'id'  # TODO: Used in SessionForm.venue_room_id; needs to be .venue_room
            'uuid_b58',
            'name',
            'title',
            'description',
            'bgcolor',
            'seq',
            'scoped_name',
        },
        'related': {
            'id'  # TODO: Used in SessionForm.venue_room_id; needs to be .venue_room
            'uuid_b58',
            'name',
            'title',
            'description',
            'bgcolor',
            'seq',
            'scoped_name',
        },
    }

    @property
    def scoped_name(self):
        return f'{self.parent.name}/{self.name}'


add_primary_relationship(Project, 'primary_venue', Venue, 'project', 'project_id')
with_roles(Project.primary_venue, read={'all'}, datasets={'primary', 'without_parent'})


@reopen(Project)
class __Project:
    venues = with_roles(
        sa.orm.relationship(
            Venue,
            cascade='all',
            order_by='Venue.seq',
            collection_class=ordering_list('seq', count_from=1),
            back_populates='project',
        ),
        read={'all'},
    )

    @property
    def rooms(self):
        return [room for venue in self.venues for room in venue.rooms]
