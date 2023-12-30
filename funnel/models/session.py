"""Session with timestamps within a project."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Self

from werkzeug.utils import cached_property

from baseframe import localize_timezone
from coaster.sqlalchemy import with_roles

from . import (
    BaseScopedIdNameMixin,
    DynamicMapped,
    Mapped,
    Model,
    Query,
    TSVectorType,
    UuidMixin,
    db,
    hybrid_property,
    relationship,
    sa,
    sa_orm,
)
from .account import Account
from .helpers import (
    ImgeeType,
    MarkdownCompositeDocument,
    add_search_trigger,
    visual_field_delimiter,
)
from .project import Project
from .project_membership import project_child_role_map
from .proposal import Proposal
from .video_mixin import VideoMixin

__all__ = ['Session']


class Session(UuidMixin, BaseScopedIdNameMixin[int, Account], VideoMixin, Model):
    __tablename__ = 'session'

    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('project.id'), default=None, nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='sessions'),
        grants_via={None: project_child_role_map},
    )
    parent: Mapped[Project] = sa_orm.synonym('project')
    description, description_text, description_html = MarkdownCompositeDocument.create(
        'description', default='', nullable=False
    )
    proposal_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('proposal.id'), default=None, nullable=True, unique=True
    )
    proposal: Mapped[Proposal | None] = relationship(back_populates='session')
    speaker: Mapped[str | None] = sa_orm.mapped_column(
        sa.Unicode(200), default=None, nullable=True
    )
    start_at: Mapped[datetime | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True, index=True
    )
    end_at: Mapped[datetime | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True, index=True
    )
    venue_room_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('venue_room.id'), default=None, nullable=True
    )
    venue_room: Mapped[VenueRoom | None] = relationship(back_populates='sessions')
    is_break: Mapped[bool] = sa_orm.mapped_column(default=False)
    featured: Mapped[bool] = sa_orm.mapped_column(default=False)
    is_restricted_video: Mapped[bool] = sa_orm.mapped_column(default=False)
    banner_image_url: Mapped[str | None] = sa_orm.mapped_column(
        ImgeeType, nullable=True
    )

    #: Version number maintained by SQLAlchemy, used for vCal files, starting at 1
    revisionid: Mapped[int] = with_roles(sa_orm.mapped_column(), read={'all'})

    search_vector: Mapped[str] = sa_orm.mapped_column(
        TSVectorType(
            'title',
            'description_text',
            'speaker',
            weights={
                'title': 'A',
                'description_text': 'B',
                'speaker': 'A',
            },
            regconfig='english',
            hltext=lambda: sa.func.concat_ws(
                visual_field_delimiter,
                Session.title,
                Session.speaker,
                Session.description_html,
            ),
        ),
        nullable=False,
        deferred=True,
    )

    saves: DynamicMapped[SavedSession] = relationship(
        lazy='dynamic', passive_deletes=True, back_populates='session'
    )

    __table_args__ = (
        sa.UniqueConstraint('project_id', 'url_id'),
        sa.CheckConstraint(
            sa.or_(
                sa.and_(start_at.is_(None), end_at.is_(None)),
                sa.and_(
                    start_at.is_not(None),
                    end_at.is_not(None),
                    end_at > start_at,
                    end_at <= start_at + timedelta(days=1),
                ),
            ),
            'session_start_at_end_at_check',
        ),
        sa.Index('ix_session_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __mapper_args__ = {'version_id_col': revisionid}

    __roles__ = {
        'all': {
            'read': {
                'created_at',
                'updated_at',
                'title',
                'project',
                'speaker',
                'user',
                'featured',
                'description',
                'start_at',
                'end_at',
                'venue_room',
                'is_break',
                'is_restricted_video',
                'banner_image_url',
                'start_at_localized',
                'end_at_localized',
                'scheduled',
                'proposal',
            },
            'call': {'url_for', 'views'},
        }
    }

    __datasets__ = {
        'primary': {
            'uuid_b58',
            'title',
            'speaker',
            'user',
            'featured',
            'description',
            'start_at',
            'end_at',
            'venue_room',
            'is_break',
            'is_restricted_video',
            'banner_image_url',
            'start_at_localized',
            'end_at_localized',
        },
        'without_parent': {
            'uuid_b58',
            'title',
            'speaker',
            'user',
            'featured',
            'description',
            'start_at',
            'end_at',
            'venue_room',
            'is_break',
            'is_restricted_video',
            'banner_image_url',
            'start_at_localized',
            'end_at_localized',
        },
        'related': {
            'uuid_b58',
            'title',
            'speaker',
            'user',
            'featured',
            'description',
            'start_at',
            'end_at',
            'venue_room',
            'is_break',
            'is_restricted_video',
            'banner_image_url',
            'start_at_localized',
            'end_at_localized',
        },
    }

    @hybrid_property
    def user(self) -> Account | None:
        if self.proposal is not None:
            return self.proposal.first_user
        return None

    @hybrid_property
    def scheduled(self) -> bool:
        # A session is scheduled only when both start and end fields have a value
        return self.start_at is not None and self.end_at is not None

    @scheduled.inplace.expression
    @classmethod
    def _scheduled_expression(cls) -> sa.ColumnElement[bool]:
        """Return SQL Expression."""
        return (cls.start_at.is_not(None)) & (cls.end_at.is_not(None))

    @cached_property
    def start_at_localized(self) -> datetime | None:
        return (
            localize_timezone(self.start_at, tz=self.project.timezone)
            if self.start_at is not None
            else None
        )

    @cached_property
    def end_at_localized(self) -> datetime | None:
        return (
            localize_timezone(self.end_at, tz=self.project.timezone)
            if self.end_at is not None
            else None
        )

    @property
    def location(self) -> str:
        """Return location as a formatted string, if available."""
        loc = []
        if self.venue_room:
            loc.append(self.venue_room.title + " - " + self.venue_room.venue.title)
            if self.venue_room.venue.city:
                loc.append(self.venue_room.venue.city)
            if self.venue_room.venue.country:
                loc.append(self.venue_room.venue.country)
        elif self.project.location:
            loc.append(self.project.location)
        return '\n'.join(loc)

    with_roles(location, read={'all'})

    @classmethod
    def for_proposal(cls, proposal: Proposal, create: bool = False) -> Session | None:
        session_obj = cls.query.filter_by(proposal=proposal).first()
        if session_obj is None and create:
            session_obj = cls(
                title=proposal.title,
                description=proposal.body,
                project=proposal.project,
                proposal=proposal,
            )
            db.session.add(session_obj)
        return session_obj

    def make_unscheduled(self) -> None:
        # Session is not deleted, but we remove start and end time,
        # so it becomes an unscheduled session.
        self.start_at = None
        self.end_at = None

    @classmethod
    def all_public(cls) -> Query[Self]:
        return cls.query.join(Project).filter(Project.state.PUBLISHED, cls.scheduled)


add_search_trigger(Session, 'search_vector')


# Tail imports
from .venue import VenueRoom

if TYPE_CHECKING:
    from .saved import SavedSession
