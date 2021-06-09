from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from typing import Optional, Type, cast

from flask_babelhg import get_locale
from werkzeug.utils import cached_property

from babel.dates import format_date
from isoweek import Week

from baseframe import localize_timezone
from coaster.sqlalchemy import with_roles
from coaster.utils import utcnow

from . import (
    BaseScopedIdNameMixin,
    MarkdownColumn,
    TSVectorType,
    UuidMixin,
    db,
    hybrid_property,
)
from .helpers import (
    ImgeeType,
    add_search_trigger,
    markdown_content_options,
    reopen,
    visual_field_delimiter,
)
from .project import Project
from .project_membership import project_child_role_map
from .proposal import Proposal
from .venue import VenueRoom
from .video_mixin import VideoMixin

__all__ = ['Session']


class Session(UuidMixin, BaseScopedIdNameMixin, VideoMixin, db.Model):
    __tablename__ = 'session'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(
            Project, backref=db.backref('sessions', cascade='all', lazy='dynamic')
        ),
        grants_via={None: project_child_role_map},
    )
    parent = db.synonym('project')
    description = MarkdownColumn(
        'description', default='', nullable=False, options=markdown_content_options
    )
    proposal_id = db.Column(
        None, db.ForeignKey('proposal.id'), nullable=True, unique=True
    )
    proposal = db.relationship(
        Proposal, backref=db.backref('session', uselist=False, cascade='all')
    )
    speaker = db.Column(db.Unicode(200), default=None, nullable=True)
    start_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)
    end_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)
    venue_room_id = db.Column(None, db.ForeignKey('venue_room.id'), nullable=True)
    venue_room = db.relationship(VenueRoom, backref=db.backref('sessions'))
    is_break = db.Column(db.Boolean, default=False, nullable=False)
    featured = db.Column(db.Boolean, default=False, nullable=False)
    banner_image_url = db.Column(ImgeeType, nullable=True)

    search_vector = db.deferred(
        db.Column(
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
                hltext=lambda: db.func.concat_ws(
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
        db.UniqueConstraint('project_id', 'url_id'),
        db.CheckConstraint(
            db.or_(
                db.and_(start_at.is_(None), end_at.is_(None)),
                db.and_(start_at.isnot(None), end_at.isnot(None), end_at > start_at),
            ),
            'session_start_at_end_at_check',
        ),
        db.Index('ix_session_search_vector', 'search_vector', postgresql_using='gin'),
    )

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
                'video',
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
    def user(self):
        if self.proposal:
            return self.proposal.first_user

    @hybrid_property
    def scheduled(self):
        # A session is scheduled only when both start and end fields have a value
        return self.start_at is not None and self.end_at is not None

    @scheduled.expression  # type: ignore[no-redef]
    def scheduled(self):
        return (self.start_at.isnot(None)) & (self.end_at.isnot(None))

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
    scheduled_sessions = db.relationship(
        Session,
        primaryjoin=db.and_(Session.venue_room_id == VenueRoom.id, Session.scheduled),
        viewonly=True,
    )


# For casting in classmethod
TypeProject = Type[Project]


@reopen(Project)
class __Project:
    # Project schedule column expressions
    # Guide: https://docs.sqlalchemy.org/en/13/orm/mapped_sql_expr.html#using-column-property
    schedule_start_at = with_roles(
        db.column_property(
            db.select([db.func.min(Session.start_at)])
            .where(Session.start_at.isnot(None))
            .where(Session.project_id == Project.id)
            .correlate_except(Session)
            .scalar_subquery()
        ),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )

    next_session_at = with_roles(
        db.column_property(
            db.select([db.func.min(Session.start_at)])
            .where(Session.start_at.isnot(None))
            .where(Session.start_at >= db.func.utcnow())
            .where(Session.project_id == Project.id)
            .correlate_except(Session)
            .scalar_subquery()
        ),
        read={'all'},
    )

    schedule_end_at = with_roles(
        db.column_property(
            db.select([db.func.max(Session.end_at)])
            .where(Session.end_at.isnot(None))
            .where(Session.project_id == Project.id)
            .correlate_except(Session)
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
        db.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=db.and_(
                Session.project_id == Project.id, Session.featured.is_(True)
            ),
            viewonly=True,
        ),
        read={'all'},
    )
    scheduled_sessions = with_roles(
        db.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=db.and_(Session.project_id == Project.id, Session.scheduled),
            viewonly=True,
        ),
        read={'all'},
    )
    unscheduled_sessions = with_roles(
        db.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=db.and_(
                Session.project_id == Project.id,
                Session.scheduled.isnot(True),  # type: ignore[attr-defined]
            ),
            viewonly=True,
        ),
        read={'all'},
    )

    sessions_with_video = with_roles(
        db.relationship(
            Session,
            lazy='dynamic',
            primaryjoin=db.and_(
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
    def next_starting_at(
        self, timestamp: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Return timestamp of next session from given timestamp.

        Supplements :attr:`next_session_at` to also consider projects without sessions.
        """
        self = cast(Project, self)
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
                db.session.query(db.func.min(Session.start_at))
                .filter(
                    Session.start_at.isnot(None),
                    Session.start_at >= timestamp,
                    Session.project == self,
                )
                .scalar()
            )

        return None

    @classmethod
    def starting_at(cls, timestamp: datetime, within: timedelta, gap: timedelta):
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
        cls = cast(TypeProject, cls)
        return (
            cls.query.filter(
                cls.id.in_(
                    db.session.query(db.func.distinct(Session.project_id)).filter(
                        Session.start_at.isnot(None),
                        Session.start_at >= timestamp,
                        Session.start_at < timestamp + within,
                        Session.project_id.notin_(
                            db.session.query(
                                db.func.distinct(Session.project_id)
                            ).filter(
                                Session.start_at.isnot(None),
                                db.or_(
                                    db.and_(
                                        Session.start_at >= timestamp - gap,
                                        Session.start_at < timestamp,
                                    ),
                                    db.and_(
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
    def current_sessions(self):
        if self.start_at is None or (self.start_at > utcnow() + timedelta(minutes=30)):
            return

        current_sessions = (
            self.sessions.outerjoin(VenueRoom)
            .filter(Session.start_at <= db.func.utcnow() + timedelta(minutes=30))
            .filter(Session.end_at > db.func.utcnow())
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

    def calendar_weeks(self, leading_weeks=True):
        # session_dates is a list of tuples in this format -
        # (date, day_start_at, day_end_at, event_count)
        if self.schedule_start_at:
            session_dates = list(
                db.session.query(
                    db.func.date_trunc(
                        'day', db.func.timezone(self.timezone.zone, Session.start_at)
                    ).label('date'),
                    db.func.min(Session.start_at).label('day_start_at'),
                    db.func.max(Session.end_at).label('day_end_at'),
                    db.func.count().label('count'),
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
        # session_dates = db.session.query(
        #     db.cast(
        #         db.func.date_trunc('day', db.func.timezone(self.timezone.zone, Session.start_at)),
        #         db.Date).label('date'),
        #     db.func.count().label('count')
        #     ).filter(
        #         Session.project == self,
        #         Session.scheduled
        #         ).group_by(db.text('date')).order_by(db.text('date'))

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

        weeks = defaultdict(dict)
        today = now.date()
        for project_date, _day_start_at, _day_end_at, session_count in session_dates:
            weekobj = Week.withdate(project_date)
            if weekobj.week not in weeks:
                weeks[weekobj.week]['year'] = weekobj.year
                # Order is important, and we need dict to count easily
                weeks[weekobj.week]['dates'] = OrderedDict()
            for wdate in weekobj.days():
                weeks[weekobj.week]['dates'].setdefault(wdate, 0)
                if project_date.date() == wdate:
                    # If the event is over don't set upcoming for current week
                    if wdate >= today and weekobj >= current_week and session_count > 0:
                        weeks[weekobj.week]['upcoming'] = True
                    weeks[weekobj.week]['dates'][wdate] += session_count
                    if 'month' not in weeks[weekobj.week]:
                        weeks[weekobj.week]['month'] = format_date(
                            wdate, 'MMM', locale=get_locale()
                        )

        # Extract sorted weeks as a list
        weeks_list = [v for k, v in sorted(weeks.items())]

        for week in weeks_list:
            # Convering to JSON messes up dictionary key order even though we used OrderedDict.
            # This turns the OrderedDict into a list of tuples and JSON preserves that order.
            week['dates'] = [
                {
                    'isoformat': date.isoformat(),
                    'day': format_date(date, 'd', get_locale()),
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
            'days': [
                format_date(day, 'EEE', locale=get_locale())
                for day in Week.thisweek().days()
            ],
        }

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def calendar_weeks_full(self):
        return self.calendar_weeks(leading_weeks=True)

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def calendar_weeks_compact(self):
        return self.calendar_weeks(leading_weeks=False)
