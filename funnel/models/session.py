"""Session with timestamps within a project."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Type
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import

from flask_babel import format_date, get_locale
from isoweek import Week
from werkzeug.utils import cached_property

from baseframe import localize_timezone
from coaster.sqlalchemy import with_roles
from coaster.utils import utcnow

from . import (
    BaseScopedIdNameMixin,
    Mapped,
    MarkdownCompositeDocument,
    TSVectorType,
    UuidMixin,
    db,
    hybrid_property,
    sa,
)
from .account import Account
from .helpers import ImgeeType, add_search_trigger, reopen, visual_field_delimiter
from .project import Project
from .project_membership import project_child_role_map
from .proposal import Proposal
from .venue import VenueRoom
from .video_mixin import VideoMixin

__all__ = ['Session']


class Session(
    UuidMixin,
    BaseScopedIdNameMixin,
    VideoMixin,
    db.Model,  # type: ignore[name-defined]
):
    __tablename__ = 'session'
    __allow_unmapped__ = True

    project_id = sa.Column(sa.Integer, sa.ForeignKey('project.id'), nullable=False)
    project: Mapped[Project] = with_roles(
        sa.orm.relationship(
            Project, backref=sa.orm.backref('sessions', cascade='all', lazy='dynamic')
        ),
        grants_via={None: project_child_role_map},
    )
    parent: Mapped[Project] = sa.orm.synonym('project')
    description = MarkdownCompositeDocument.create(
        'description', default='', nullable=False
    )
    proposal_id = sa.Column(
        sa.Integer, sa.ForeignKey('proposal.id'), nullable=True, unique=True
    )
    proposal: Mapped[Optional[Proposal]] = sa.orm.relationship(
        Proposal, backref=sa.orm.backref('session', uselist=False, cascade='all')
    )
    speaker = sa.Column(sa.Unicode(200), default=None, nullable=True)
    start_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True, index=True)
    end_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True, index=True)
    venue_room_id = sa.Column(sa.Integer, sa.ForeignKey('venue_room.id'), nullable=True)
    venue_room: Mapped[Optional[VenueRoom]] = sa.orm.relationship(
        VenueRoom, backref=sa.orm.backref('sessions')
    )
    is_break = sa.Column(sa.Boolean, default=False, nullable=False)
    featured = sa.Column(sa.Boolean, default=False, nullable=False)
    banner_image_url: Mapped[Optional[str]] = sa.Column(ImgeeType, nullable=True)

    #: Version number maintained by SQLAlchemy, used for vCal files, starting at 1
    revisionid = with_roles(sa.Column(sa.Integer, nullable=False), read={'all'})

    search_vector: Mapped[str] = sa.orm.deferred(
        sa.Column(
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
        )
    )

    __table_args__ = (
        sa.UniqueConstraint('project_id', 'url_id'),
        sa.CheckConstraint(
            sa.or_(  # type: ignore[arg-type]
                sa.and_(start_at.is_(None), end_at.is_(None)),
                sa.and_(
                    start_at.isnot(None),
                    end_at.isnot(None),
                    end_at > start_at,
                    end_at <= start_at + sa.text("INTERVAL '1 day'"),
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
            'banner_image_url',
            'start_at_localized',
            'end_at_localized',
        },
    }

    @hybrid_property
    def user(self) -> Optional[Account]:
        if self.proposal is not None:
            return self.proposal.first_user
        return None  # type: ignore[unreachable]

    @hybrid_property
    def scheduled(self):
        # A session is scheduled only when both start and end fields have a value
        return self.start_at is not None and self.end_at is not None

    @scheduled.inplace.expression
    @classmethod
    def _scheduled_expression(cls):
        return (cls.start_at.isnot(None)) & (cls.end_at.isnot(None))

    @cached_property
    def start_at_localized(self):
        return (
            localize_timezone(self.start_at, tz=self.project.timezone)
            if self.start_at
            else None
        )

    @cached_property
    def end_at_localized(self):
        return (
            localize_timezone(self.end_at, tz=self.project.timezone)
            if self.end_at
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
    def for_proposal(cls, proposal, create=False):
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

    def make_unscheduled(self):
        # Session is not deleted, but we remove start and end time,
        # so it becomes an unscheduled session.
        self.start_at = None
        self.end_at = None

    @classmethod
    def all_public(cls):
        return cls.query.join(Project).filter(Project.state.PUBLISHED, cls.scheduled)


add_search_trigger(Session, 'search_vector')


@reopen(VenueRoom)
class __VenueRoom:
    scheduled_sessions = sa.orm.relationship(
        Session,
        primaryjoin=sa.and_(
            Session.venue_room_id == VenueRoom.id,
            Session.scheduled,  # type: ignore[arg-type]
        ),
        viewonly=True,
    )


@reopen(Project)
class __Project:
    # Project schedule column expressions. Guide:
    # https://docs.sqlalchemy.org/en/13/orm/mapped_sql_expr.html#using-column-property
    schedule_start_at = with_roles(
        sa.orm.column_property(
            sa.select(sa.func.min(Session.start_at))
            .where(Session.start_at.isnot(None))
            .where(Session.project_id == Project.id)
            .correlate_except(Session)  # type: ignore[arg-type]
            .scalar_subquery()
        ),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )

    next_session_at = with_roles(
        sa.orm.column_property(
            sa.select(sa.func.min(sa.column('start_at')))
            .select_from(
                sa.select(sa.func.min(Session.start_at).label('start_at'))
                .where(Session.start_at.isnot(None))
                .where(Session.start_at >= sa.func.utcnow())
                .where(Session.project_id == Project.id)
                .correlate_except(Session)  # type: ignore[arg-type]
                .union(
                    sa.select(
                        Project.start_at.label('start_at')  # type: ignore[has-type]
                    )
                    .where(Project.start_at.isnot(None))  # type: ignore[has-type]
                    .where(
                        Project.start_at >= sa.func.utcnow()  # type: ignore[has-type]
                    )
                    .correlate(Project)  # type: ignore[arg-type]
                )
            )
            .scalar_subquery()
        ),
        read={'all'},
    )

    schedule_end_at = with_roles(
        sa.orm.column_property(
            sa.select(sa.func.max(Session.end_at))
            .where(Session.end_at.isnot(None))
            .where(Session.project_id == Project.id)
            .correlate_except(Session)  # type: ignore[arg-type]
            .scalar_subquery()
        ),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def schedule_start_at_localized(self):
        return (
            localize_timezone(self.schedule_start_at, tz=self.timezone)
            if self.schedule_start_at
            else None
        )

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def schedule_end_at_localized(self):
        return (
            localize_timezone(self.schedule_end_at, tz=self.timezone)
            if self.schedule_end_at
            else None
        )

    @with_roles(read={'all'})
    @cached_property
    def session_count(self):
        return self.sessions.filter(Session.start_at.isnot(None)).count()

    featured_sessions = with_roles(
        sa.orm.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=sa.and_(
                Session.project_id == Project.id, Session.featured.is_(True)
            ),
            viewonly=True,
        ),
        read={'all'},
    )
    scheduled_sessions = with_roles(
        sa.orm.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=sa.and_(
                Session.project_id == Project.id,
                Session.scheduled,  # type: ignore[arg-type]
            ),
            viewonly=True,
        ),
        read={'all'},
    )
    unscheduled_sessions = with_roles(
        sa.orm.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=sa.and_(
                Session.project_id == Project.id,
                Session.scheduled.isnot(True),  # type: ignore[attr-defined]
            ),
            viewonly=True,
        ),
        read={'all'},
    )

    sessions_with_video = with_roles(
        sa.orm.relationship(
            Session,
            lazy='dynamic',
            primaryjoin=sa.and_(
                Project.id == Session.project_id,
                Session.video_id.isnot(None),
                Session.video_source.isnot(None),
            ),
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sessions_with_video(self):
        return self.query.session.query(self.sessions_with_video.exists()).scalar()

    def next_session_from(self, timestamp):
        """Find the next session in this project from given timestamp."""
        return (
            self.sessions.filter(
                Session.start_at.isnot(None), Session.start_at >= timestamp
            )
            .order_by(Session.start_at.asc())
            .first()
        )

    @with_roles(call={'all'})
    def next_starting_at(  # type: ignore[misc]
        self: Project, timestamp: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Return timestamp of next session from given timestamp.

        Supplements :attr:`next_session_at` to also consider projects without sessions.
        """
        # If there's no `self.start_at`, there is no session either
        if self.start_at is not None:
            if timestamp is None:
                timestamp = utcnow()
            # If `self.start_at` is in the future, it is guaranteed to be the closest
            # timestamp, so return it directly
            if self.start_at >= timestamp:
                return self.start_at
            # In the past? Then look for a session and return that timestamp, if any
            return (
                db.session.query(sa.func.min(Session.start_at))
                .filter(
                    Session.start_at.isnot(None),
                    Session.start_at >= timestamp,
                    Session.project == self,
                )
                .scalar()
            )

        return None

    @classmethod
    def starting_at(  # type: ignore[misc]
        cls: Type[Project], timestamp: datetime, within: timedelta, gap: timedelta
    ):
        """
        Return projects that are about to start, for sending notifications.

        :param datetime timestamp: The timestamp to look for new sessions at
        :param timedelta within: Find anything at timestamp + within delta. Lookup will
            be for sessions where timestamp >= start_at < timestamp+within
        :param timedelta gap: A project will be considered to be starting if it has no
            sessions ending within the gap period before the timestamp

        Typical use of this method is from a background worker that calls it at
        intervals of five minutes with parameters (timestamp, within 5m, 60m gap).
        """
        # As a rule, start_at is queried with >= and <, end_at with > and <= because
        # they represent inclusive lower and upper bounds.

        # Check project starting time before looking for individual sessions, as some
        # projects will have no sessions
        return (
            cls.query.filter(
                cls.id.in_(
                    db.session.query(sa.func.distinct(Session.project_id)).filter(
                        Session.start_at.isnot(None),
                        Session.start_at >= timestamp,
                        Session.start_at < timestamp + within,
                        Session.project_id.notin_(
                            db.session.query(
                                sa.func.distinct(Session.project_id)
                            ).filter(
                                Session.start_at.isnot(None),
                                sa.or_(
                                    sa.and_(
                                        Session.start_at >= timestamp - gap,
                                        Session.start_at < timestamp,
                                    ),
                                    sa.and_(
                                        Session.end_at > timestamp - gap,
                                        Session.end_at <= timestamp,
                                    ),
                                ),
                            )
                        ),
                    )
                )
            )
            .join(Session.project)
            .filter(cls.state.PUBLISHED)
        ).union(
            cls.query.filter(
                cls.state.PUBLISHED,
                cls.start_at.isnot(None),
                cls.start_at >= timestamp,
                cls.start_at < timestamp + within,
            )
        )

    @with_roles(call={'all'})
    def current_sessions(self: Project) -> Optional[dict]:  # type: ignore[misc]
        if self.start_at is None or (self.start_at > utcnow() + timedelta(minutes=30)):
            return None

        current_sessions = (
            self.sessions.outerjoin(VenueRoom)
            .filter(Session.start_at <= sa.func.utcnow() + timedelta(minutes=30))
            .filter(Session.end_at > sa.func.utcnow())
            .order_by(Session.start_at.asc(), VenueRoom.seq.asc())
        )

        return {
            'sessions': [
                session.current_access(datasets=('without_parent', 'related'))
                for session in current_sessions
            ],
            'rooms': [
                room.current_access(datasets=('without_parent', 'related'))
                for room in self.rooms
            ],
        }

    def calendar_weeks(self: Project, leading_weeks=True):  # type: ignore[misc]
        # session_dates is a list of tuples in this format -
        # (date, day_start_at, day_end_at, event_count)
        if self.schedule_start_at:
            session_dates = list(
                db.session.query(
                    sa.func.date_trunc(
                        'day', sa.func.timezone(self.timezone.zone, Session.start_at)
                    ).label('date'),
                    sa.func.min(Session.start_at).label('day_start_at'),
                    sa.func.max(Session.end_at).label('day_end_at'),
                    sa.func.count().label('count'),
                )
                .select_from(Session)
                .filter(
                    Session.project == self,
                    Session.start_at.isnot(None),
                    Session.end_at.isnot(None),
                )
                .group_by('date')
                .order_by('date')
            )
        elif self.start_at:
            start_at = self.start_at_localized
            end_at = self.end_at_localized
            if start_at.date() == end_at.date():
                session_dates = [(start_at, start_at, end_at, 1)]
            else:
                session_dates = [
                    (
                        start_at + timedelta(days=plusdays),
                        start_at + timedelta(days=plusdays),
                        end_at - timedelta(days=plusdays),
                        1,
                    )
                    for plusdays in range(
                        (
                            end_at.replace(hour=1, minute=0, second=0, microsecond=0)
                            - start_at.replace(
                                hour=0, minute=0, second=0, microsecond=0
                            )
                        ).days
                        + 1
                    )
                ]
        else:
            session_dates = []

        session_dates_dict = {
            date.date(): {
                'day_start_at': day_start_at,
                'day_end_at': day_end_at,
                'count': count,
            }
            for date, day_start_at, day_end_at, count in session_dates
        }

        # FIXME: This doesn't work. This code needs to be tested in isolation
        # session_dates = (
        #     db.session.query(
        #         sa.cast(
        #             sa.func.date_trunc(
        #                 'day', sa.func.timezone(self.timezone.zone, Session.start_at)
        #             ),
        #             sa.Date,
        #         ).label('date'),
        #         sa.func.count().label('count'),
        #     )
        #     .filter(Session.project == self, Session.scheduled)
        #     .group_by(sa.text('date'))
        #     .order_by(sa.text('date'))
        # )

        # if the project's week is within next 2 weeks, send current week as well
        now = utcnow().astimezone(self.timezone)
        current_week = Week.withdate(now)

        if leading_weeks and self.schedule_start_at is not None:
            schedule_start_week = Week.withdate(self.schedule_start_at)

            # session_dates is a list of tuples in this format -
            # (date, day_start_at, day_end_at, event_count)
            # as these days dont have any event, day_start/end_at are None,
            # and count is 0.
            if (
                schedule_start_week > current_week
                and (schedule_start_week - current_week) <= 2
            ):
                if (schedule_start_week - current_week) == 2:
                    # add this so that the next week's dates
                    # are also included in the calendar.
                    session_dates.insert(0, (now + timedelta(days=7), None, None, 0))
                session_dates.insert(0, (now, None, None, 0))

        weeks: Dict[str, Dict[str, Any]] = defaultdict(dict)
        today = now.date()
        for project_date, _day_start_at, _day_end_at, session_count in session_dates:
            weekobj = Week.withdate(project_date)
            weekid = weekobj.isoformat()
            if weekid not in weeks:
                weeks[weekid]['year'] = weekobj.year
                # Order is important, and we need dict to count easily
                weeks[weekid]['dates'] = OrderedDict()
            for wdate in weekobj.days():
                weeks[weekid]['dates'].setdefault(wdate, 0)
                if project_date.date() == wdate:
                    # If the event is over don't set upcoming for current week
                    if wdate >= today and weekobj >= current_week and session_count > 0:
                        weeks[weekid]['upcoming'] = True
                    weeks[weekid]['dates'][wdate] += session_count
                    if 'month' not in weeks[weekid]:
                        weeks[weekid]['month'] = format_date(wdate, 'MMM')
        # Extract sorted weeks as a list
        weeks_list = [v for k, v in sorted(weeks.items())]

        for week in weeks_list:
            # Convering to JSON messes up dictionary key order even though we used
            # OrderedDict. This turns the OrderedDict into a list of tuples and JSON
            # preserves that order.
            week['dates'] = [
                {
                    'isoformat': date.isoformat(),
                    'day': format_date(date, 'd'),
                    'count': count,
                    'day_start_at': (
                        session_dates_dict[date]['day_start_at']
                        .astimezone(self.timezone)
                        .strftime('%I:%M %p')
                        if date in session_dates_dict.keys()
                        else None
                    ),
                    'day_end_at': (
                        session_dates_dict[date]['day_end_at']
                        .astimezone(self.timezone)
                        .strftime('%I:%M %p %Z')
                        if date in session_dates_dict.keys()
                        else None
                    ),
                }
                for date, count in week['dates'].items()
            ]
        return {
            'locale': get_locale(),
            'weeks': weeks_list,
            'today': now.date().isoformat(),
            'days': [format_date(day, 'EEE') for day in Week.thisweek().days()],
        }

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def calendar_weeks_full(self):
        return self.calendar_weeks(leading_weeks=True)

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def calendar_weeks_compact(self):
        return self.calendar_weeks(leading_weeks=False)
