"""Model for project venue and rooms within a venue (legacy, pending global venues)."""

from __future__ import annotations

from sqlalchemy.ext.orderinglist import OrderingList, ordering_list

from coaster.sqlalchemy import add_primary_relationship, with_roles

from . import (
    BaseScopedNameMixin,
    CoordinatesMixin,
    Mapped,
    Model,
    UuidMixin,
    relationship,
    sa,
    sa_orm,
)
from .account import Account
from .helpers import MarkdownCompositeBasic
from .project import Project
from .project_membership import project_child_role_map, project_child_role_set

__all__ = ['Venue', 'VenueRoom']


class Venue(UuidMixin, BaseScopedNameMixin[int, Account], CoordinatesMixin, Model):
    __tablename__ = 'venue'

    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('project.id'), default=None, nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='venues'), grants_via={None: project_child_role_map}
    )
    parent: Mapped[Project] = sa_orm.synonym('project')
    description, description_text, description_html = MarkdownCompositeBasic.create(
        'description', default='', nullable=False
    )
    address1: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(160), default='', nullable=False
    )
    address2: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(160), default='', nullable=False
    )
    city: Mapped[str] = sa_orm.mapped_column(sa.Unicode(30), default='', nullable=False)
    state: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(30), default='', nullable=False
    )
    postcode: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(20), default='', nullable=False
    )
    country: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(2), default='', nullable=False
    )

    rooms: Mapped[OrderingList[VenueRoom]] = relationship(
        order_by=lambda: VenueRoom.seq,
        collection_class=ordering_list('seq', count_from=1),
        back_populates='venue',
    )

    seq: Mapped[int] = sa_orm.mapped_column()

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


class VenueRoom(UuidMixin, BaseScopedNameMixin[int, Account], Model):
    __tablename__ = 'venue_room'

    venue_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('venue.id'), default=None, nullable=False
    )
    venue: Mapped[Venue] = with_roles(
        relationship(back_populates='rooms'),
        # Since Venue already remaps Project roles, we just want the remapped role names
        grants_via={None: project_child_role_set},
    )
    parent: Mapped[Venue] = sa_orm.synonym('venue')
    description, description_text, description_html = MarkdownCompositeBasic.create(
        'description', default='', nullable=False
    )
    bgcolor: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(6), nullable=False, default='229922'
    )

    seq: Mapped[int] = sa_orm.mapped_column()

    sessions: Mapped[list[Session]] = relationship(back_populates='venue_room')
    scheduled_sessions: Mapped[list[Session]] = relationship(
        primaryjoin=lambda: sa.and_(
            Session.venue_room_id == VenueRoom.id,
            Session.scheduled,  # type: ignore[has-type]  # FIXME
        ),
        viewonly=True,
    )

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


# Tail imports
from .session import Session
