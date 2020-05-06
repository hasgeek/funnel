# -*- coding: utf-8 -*-

from collections import OrderedDict, defaultdict
from datetime import timedelta

from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy_utils import TimezoneType

from flask import current_app
from werkzeug.utils import cached_property

from babel.dates import format_date
from isoweek import Week
from pytz import utc

from baseframe import __, get_locale, localize_timezone
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum, buid, utcnow, valid_username

from ..utils import geonameid_from_location
from . import (
    BaseScopedNameMixin,
    JsonDict,
    MarkdownColumn,
    TimestampMixin,
    TSVectorType,
    UrlType,
    UuidMixin,
    db,
)
from .commentvote import SET_TYPE, Commentset, Voteset
from .helpers import RESERVED_NAMES, add_search_trigger
from .profile import Profile
from .user import User

__all__ = ['Project', 'ProjectLocation', 'ProjectRedirect']


# --- Constants ---------------------------------------------------------------


class PROJECT_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))
    WITHDRAWN = (2, 'withdrawn', __("Withdrawn"))
    DELETED = (3, 'deleted', __("Deleted"))
    DELETABLE = {DRAFT, PUBLISHED, WITHDRAWN}
    PUBLISHABLE = {DRAFT, WITHDRAWN}


class CFP_STATE(LabeledEnum):  # NOQA: N801
    NONE = (0, 'none', __("None"))
    PUBLIC = (1, 'public', __("Public"))
    CLOSED = (2, 'closed', __("Closed"))
    OPENABLE = {NONE, CLOSED}
    EXISTS = {PUBLIC, CLOSED}


class SCHEDULE_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))


# --- Models ------------------------------------------------------------------


class Project(UuidMixin, BaseScopedNameMixin, db.Model):
    __tablename__ = 'project'
    reserved_names = RESERVED_NAMES

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('projects', cascade='all'),
    )
    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False)
    profile = db.relationship(
        'Profile', backref=db.backref('projects', cascade='all', lazy='dynamic')
    )
    parent = db.synonym('profile')
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = MarkdownColumn('description', default='', nullable=False)
    instructions = MarkdownColumn('instructions', default='', nullable=True)

    location = db.Column(db.Unicode(50), default='', nullable=True)
    parsed_location = db.Column(JsonDict, nullable=False, server_default='{}')

    website = db.Column(UrlType, nullable=True)
    timezone = db.Column(TimezoneType(backend='pytz'), nullable=False, default=utc)

    _state = db.Column(
        'state',
        db.Integer,
        StateManager.check_constraint('state', PROJECT_STATE),
        default=PROJECT_STATE.DRAFT,
        nullable=False,
    )
    state = StateManager('_state', PROJECT_STATE, doc="Project state")
    _cfp_state = db.Column(
        'cfp_state',
        db.Integer,
        StateManager.check_constraint('cfp_state', CFP_STATE),
        default=CFP_STATE.NONE,
        nullable=False,
    )
    cfp_state = StateManager('_cfp_state', CFP_STATE, doc="CfP state")
    _schedule_state = db.Column(
        'schedule_state',
        db.Integer,
        StateManager.check_constraint('schedule_state', SCHEDULE_STATE),
        default=SCHEDULE_STATE.DRAFT,
        nullable=False,
    )
    schedule_state = StateManager(
        '_schedule_state', SCHEDULE_STATE, doc="Schedule state"
    )

    cfp_start_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    cfp_end_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    # Columns for mobile
    bg_image = db.Column(UrlType, nullable=True)
    bg_color = db.Column(db.Unicode(6), nullable=True)
    explore_url = db.Column(UrlType, nullable=True)
    allow_rsvp = db.Column(db.Boolean, default=False, nullable=False)
    buy_tickets_url = db.Column(UrlType, nullable=True)

    banner_video_url = db.Column(UrlType, nullable=True)
    boxoffice_data = db.Column(JsonDict, nullable=False, server_default='{}')

    hasjob_embed_url = db.Column(UrlType, nullable=True)
    hasjob_embed_limit = db.Column(db.Integer, default=8)

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(Commentset, uselist=False)

    parent_id = db.Column(
        None, db.ForeignKey('project.id', ondelete='SET NULL'), nullable=True
    )
    parent_project = db.relationship(
        'Project', remote_side='Project.id', backref='subprojects'
    )

    #: Featured project flag. This can only be set by website editors, not
    #: project editors or profile admins.
    featured = db.Column(db.Boolean, default=False, nullable=False)

    search_vector = db.deferred(
        db.Column(
            TSVectorType(
                'name',
                'title',
                'description_text',
                'instructions_text',
                'location',
                weights={
                    'name': 'A',
                    'title': 'A',
                    'description_text': 'B',
                    'instructions_text': 'B',
                    'location': 'C',
                },
                regconfig='english',
                hltext=lambda: db.func.concat_ws(
                    ' / ',
                    Project.title,
                    Project.location,
                    Project.description_html,
                    Project.instructions_html,
                ),
            ),
            nullable=False,
        )
    )

    livestream_urls = db.Column(
        db.ARRAY(db.UnicodeText, dimensions=1), server_default='{}'
    )

    venues = db.relationship(
        'Venue',
        cascade='all',
        order_by='Venue.seq',
        collection_class=ordering_list('seq', count_from=1),
    )
    labels = db.relationship(
        'Label',
        cascade='all',
        primaryjoin='and_(Label.project_id == Project.id, Label.main_label_id == None, Label._archived == False)',
        order_by='Label.seq',
        collection_class=ordering_list('seq', count_from=1),
    )
    all_labels = db.relationship('Label', lazy='dynamic')

    featured_sessions = db.relationship(
        'Session',
        order_by="Session.start_at.asc()",
        primaryjoin='and_(Session.project_id == Project.id, Session.featured == True)',
    )
    scheduled_sessions = db.relationship(
        'Session',
        order_by="Session.start_at.asc()",
        primaryjoin='and_(Session.project_id == Project.id, Session.scheduled)',
    )
    unscheduled_sessions = db.relationship(
        'Session',
        order_by="Session.start_at.asc()",
        primaryjoin='and_(Session.project_id == Project.id, Session.scheduled != True)',
    )

    __table_args__ = (
        db.UniqueConstraint('profile_id', 'name'),
        db.Index('ix_project_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __roles__ = {
        'all': {
            'read': {
                'id',
                'name',
                'title',
                'title_inline',
                'datelocation',
                'timezone',
                'schedule_start_at',
                'schedule_end_at',
                'url_json',
                'website',
                'bg_image',
                'bg_color',
                'explore_url',
                'tagline',
                'absolute_url',
                'location',
                'calendar_weeks_full',
                'calendar_weeks_compact',
                'primary_venue',
                'livestream_urls',
                'schedule_start_at_localized',
                'schedule_end_at_localized',
                'cfp_start_at_localized',
                'cfp_end_at_localized',
            },
            'call': {'url_for', 'current_sessions', 'is_saved_by', 'schedule_state'},
        }
    }

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        self.voteset = Voteset(settype=SET_TYPE.PROJECT)
        self.commentset = Commentset(settype=SET_TYPE.PROJECT)
        # Add the creator as editor and concierge
        new_membership = ProjectCrewMembership(
            parent=self,
            user=self.user,
            granted_by=self.user,
            is_editor=True,
            is_concierge=True,
        )
        db.session.add(new_membership)

    def __repr__(self):
        return '<Project %s/%s "%s">' % (
            self.profile.name if self.profile else "(none)",
            self.name,
            self.title,
        )

    @classmethod
    def migrate_profile(cls, old_profile, new_profile):
        names = {project.name for project in new_profile.projects}
        for project in old_profile.projects:
            if project.name in names:
                current_app.logger.warning(
                    "Project %r had a conflicting name in profile migration, "
                    "so renaming by adding adding random value to name",
                    project,
                )
                project.name += '-' + buid()
            project.profile = new_profile

    @property
    def title_inline(self):
        """Suffix a colon if the title does not end in ASCII sentence punctuation"""
        if self.title and self.tagline:
            if not self.title[-1] in ('?', '!', ':', ';', '.', ','):
                return self.title + ':'
        return self.title

    @property
    def datelocation(self):
        """
        Returns a date + location string for the event, the format depends on project dates

        If it's a single day event
        > 11 Feb 2018, Bangalore

        If multi-day event in same month
        > 09–12 Feb 2018, Bangalore

        If multi-day event across months
        > 27 Feb–02 Mar 2018, Bangalore

        If multi-day event across years
        > 30 Dec 2018–02 Jan 2019, Bangalore

        ``datelocation_format`` always keeps ``schedule_end_at`` format as ``–DD Mmm YYYY``.
        Depending on the scenario mentioned below, format for ``schedule_start_at`` changes. Above examples
        demonstrate the same. All the possible outputs end with ``–DD Mmm YYYY, Venue``.
        Only ``schedule_start_at`` format changes.
        """
        daterange = ""
        if self.schedule_start_at is not None and self.schedule_end_at is not None:
            schedule_start_at_date = self.schedule_start_at.astimezone(
                self.timezone
            ).date()
            schedule_end_at_date = self.schedule_end_at.astimezone(self.timezone).date()
            daterange_format = "{start_date}–{end_date} {year}"
            if schedule_start_at_date == schedule_end_at_date:
                # if both dates are same, in case of single day project
                strf_date = ""
                daterange_format = "{end_date} {year}"
            elif schedule_start_at_date.year != schedule_end_at_date.year:
                # if the start date and end dates are in different years,
                strf_date = "%d %b %Y"
            elif schedule_start_at_date.month != schedule_end_at_date.month:
                # If multi-day event across months
                strf_date = "%d %b"
            elif schedule_start_at_date.month == schedule_end_at_date.month:
                # If multi-day event in same month
                strf_date = "%d"
            daterange = daterange_format.format(
                start_date=schedule_start_at_date.strftime(strf_date),
                end_date=schedule_end_at_date.strftime("%d %b"),
                year=schedule_end_at_date.year,
            )
        return ', '.join([_f for _f in [daterange, self.location] if _f])

    schedule_state.add_conditional_state(
        'PAST',
        schedule_state.PUBLISHED,
        lambda project: project.schedule_end_at is not None
        and utcnow() >= project.schedule_end_at,
        lambda project: db.func.utcnow() >= project.schedule_end_at,
        label=('past', __("Past")),
    )
    schedule_state.add_conditional_state(
        'LIVE',
        schedule_state.PUBLISHED,
        lambda project: (
            project.schedule_start_at is not None
            and project.schedule_start_at <= utcnow() < project.schedule_end_at
        ),
        lambda project: db.and_(
            project.schedule_start_at <= db.func.utcnow(),
            db.func.utcnow() < project.schedule_end_at,
        ),
        label=('live', __("Live")),
    )
    schedule_state.add_conditional_state(
        'UPCOMING',
        schedule_state.PUBLISHED,
        lambda project: project.schedule_start_at is not None
        and utcnow() < project.schedule_start_at,
        lambda project: db.func.utcnow() < project.schedule_start_at,
        label=('upcoming', __("Upcoming")),
    )

    cfp_state.add_conditional_state(
        'HAS_PROPOSALS',
        cfp_state.EXISTS,
        lambda project: db.session.query(project.proposals.exists()).scalar(),
        label=('has_proposals', __("Has Proposals")),
    )
    cfp_state.add_conditional_state(
        'HAS_SESSIONS',
        cfp_state.EXISTS,
        lambda project: db.session.query(project.sessions.exists()).scalar(),
        label=('has_sessions', __("Has Sessions")),
    )
    cfp_state.add_conditional_state(
        'PRIVATE_DRAFT',
        cfp_state.NONE,
        lambda project: project.instructions_html != '',
        lambda project: db.and_(
            project.instructions_html.isnot(None), project.instructions_html != ''
        ),
        label=('private_draft', __("Private draft")),
    )
    cfp_state.add_conditional_state(
        'DRAFT',
        cfp_state.PUBLIC,
        lambda project: project.cfp_start_at is None,
        lambda project: project.cfp_start_at.is_(None),
        label=('draft', __("Draft")),
    )
    cfp_state.add_conditional_state(
        'UPCOMING',
        cfp_state.PUBLIC,
        lambda project: project.cfp_start_at is not None
        and utcnow() < project.cfp_start_at,
        lambda project: db.and_(
            project.cfp_start_at.isnot(None), db.func.utcnow() < project.cfp_start_at
        ),
        label=('upcoming', __("Upcoming")),
    )
    cfp_state.add_conditional_state(
        'OPEN',
        cfp_state.PUBLIC,
        lambda project: project.cfp_start_at is not None
        and project.cfp_start_at <= utcnow()
        and (project.cfp_end_at is None or utcnow() < project.cfp_end_at),
        lambda project: db.and_(
            project.cfp_start_at.isnot(None),
            project.cfp_start_at <= db.func.utcnow(),
            db.or_(project.cfp_end_at.is_(None), db.func.utcnow() < project.cfp_end_at),
        ),
        label=('open', __("Open")),
    )
    cfp_state.add_conditional_state(
        'EXPIRED',
        cfp_state.PUBLIC,
        lambda project: project.cfp_end_at is not None
        and utcnow() >= project.cfp_end_at,
        lambda project: db.and_(
            project.cfp_end_at.isnot(None), db.func.utcnow() >= project.cfp_end_at
        ),
        label=('expired', __("Expired")),
    )

    cfp_state.add_state_group('UNAVAILABLE', cfp_state.CLOSED, cfp_state.EXPIRED)

    @with_roles(call={'editor'})
    @cfp_state.transition(
        cfp_state.OPENABLE,
        cfp_state.PUBLIC,
        title=__("Enable proposal submissions"),
        message=__("Proposals can be now submitted"),
        type='success',
    )
    def open_cfp(self):
        pass

    @with_roles(call={'editor'})
    @cfp_state.transition(
        cfp_state.PUBLIC,
        cfp_state.CLOSED,
        title=__("Disable proposal submissions"),
        message=__("Proposals will no longer be accepted"),
        type='success',
    )
    def close_cfp(self):
        pass

    @with_roles(call={'editor'})
    @schedule_state.transition(
        schedule_state.DRAFT,
        schedule_state.PUBLISHED,
        title=__("Publish schedule"),
        message=__("The schedule has been published"),
        type='success',
    )
    def publish_schedule(self):
        pass

    @with_roles(call={'editor'})
    @schedule_state.transition(
        schedule_state.PUBLISHED,
        schedule_state.DRAFT,
        title=__("Unpublish schedule"),
        message=__("The schedule has been moved to draft state"),
        type='success',
    )
    def unpublish_schedule(self):
        pass

    @with_roles(call={'editor'})
    @state.transition(
        state.PUBLISHABLE,
        state.PUBLISHED,
        title=__("Publish project"),
        message=__("The project has been published"),
        type='success',
    )
    def publish(self):
        pass

    @with_roles(call={'editor'})
    @state.transition(
        state.PUBLISHED,
        state.WITHDRAWN,
        title=__("Withdraw project"),
        message=__("The project has been withdrawn and is no longer listed"),
        type='success',
    )
    def withdraw(self):
        pass

    # Removing Delete feature till we figure out siteadmin feature
    # @with_roles(call={'editor'})
    # @state.transition(
    #     state.DELETABLE, state.DELETED, title=__("Delete project"),
    #     message=__("The project has been deleted"), type='success')
    # def delete(self):
    #     pass

    @property
    def url_json(self):
        return self.url_for('json', _external=True)

    @db.validates('name')
    def _validate_name(self, key, value):
        value = value.strip() if value is not None else None
        if not value or not valid_username(value):
            raise ValueError(value)

        if value != self.name and self.name is not None and self.profile is not None:
            redirect = ProjectRedirect.query.get((self.profile_id, self.name))
            if redirect is None:
                redirect = ProjectRedirect(
                    profile=self.profile, name=self.name, project=self
                )
                db.session.add(redirect)
            else:
                redirect.project = self
        return value

    def calendar_weeks(self, leading_weeks=True):
        # session_dates is a list of tuples in this format -
        # (date, day_start_at, day_end_at, event_count)
        session_dates = list(
            db.session.query('date', 'day_start_at', 'day_end_at', 'count')
            .from_statement(
                db.text(
                    '''
                    SELECT
                        DATE_TRUNC('day', "start_at" AT TIME ZONE :timezone) AS date,
                        MIN(start_at) as day_start_at,
                        MAX(end_at) as day_end_at,
                        COUNT(*) AS count
                    FROM "session" WHERE "project_id" = :project_id AND "start_at" IS NOT NULL AND "end_at" IS NOT NULL
                    GROUP BY date ORDER BY date;
                    '''
                )
            )
            .params(timezone=self.timezone.zone, project_id=self.id)
        )

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
        for project_date, day_start_at, day_end_at, session_count in session_dates:
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
                        .strftime("%I:%M %p")
                        if date in session_dates_dict.keys()
                        else None
                    ),
                    'day_end_at': (
                        session_dates_dict[date]['day_end_at']
                        .astimezone(self.timezone)
                        .strftime("%I:%M %p %Z")
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

    @cached_property
    def calendar_weeks_full(self):
        return self.calendar_weeks(leading_weeks=True)

    @cached_property
    def calendar_weeks_compact(self):
        return self.calendar_weeks(leading_weeks=False)

    @cached_property
    def schedule_start_at_localized(self):
        return (
            localize_timezone(self.schedule_start_at, tz=self.timezone)
            if self.schedule_start_at
            else None
        )

    @cached_property
    def schedule_end_at_localized(self):
        return (
            localize_timezone(self.schedule_end_at, tz=self.timezone)
            if self.schedule_end_at
            else None
        )

    @cached_property
    def cfp_start_at_localized(self):
        return (
            localize_timezone(self.cfp_start_at, tz=self.timezone)
            if self.cfp_start_at
            else None
        )

    @cached_property
    def cfp_end_at_localized(self):
        return (
            localize_timezone(self.cfp_end_at, tz=self.timezone)
            if self.cfp_end_at
            else None
        )

    def current_sessions(self):
        now = utcnow().astimezone(self.timezone)

        if self.schedule_start_at is None or self.schedule_start_at > now + timedelta(
            minutes=30
        ):
            return

        current_sessions = (
            self.sessions.join(VenueRoom)
            .filter(Session.scheduled)
            .filter(Session.start_at <= now + timedelta(minutes=30))
            .filter(Session.end_at > now)
            .order_by(Session.start_at.asc(), VenueRoom.seq.asc())
        )

        return {
            'sessions': [session.current_access() for session in current_sessions],
            'rooms': [room.current_access() for room in self.rooms],
        }

    @property
    def rooms(self):
        return [room for venue in self.venues for room in venue.rooms]

    @property
    def proposals_all(self):
        from .proposal import Proposal

        if self.subprojects:
            return Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
            return self.proposals

    @property
    def proposals_by_state(self):
        from .proposal import Proposal

        if self.subprojects:
            basequery = Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
            basequery = Proposal.query.filter_by(project=self)
        return Proposal.state.group(
            basequery.filter(
                ~(Proposal.state.DRAFT), ~(Proposal.state.DELETED)
            ).order_by(db.desc('created_at'))
        )

    @property
    def proposals_by_confirmation(self):
        from .proposal import Proposal

        if self.subprojects:
            basequery = Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
            basequery = Proposal.query.filter_by(project=self)
        return {
            'confirmed': basequery.filter(Proposal.state.CONFIRMED)
            .order_by(db.desc('created_at'))
            .all(),
            'unconfirmed': basequery.filter(
                ~(Proposal.state.CONFIRMED),
                ~(Proposal.state.DRAFT),
                ~(Proposal.state.DELETED),
            )
            .order_by(db.desc('created_at'))
            .all(),
        }

    @cached_property
    def location_geonameid(self):
        return geonameid_from_location(self.location) if self.location else set()

    def permissions(self, user, inherited=None):
        perms = super(Project, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            if self.cfp_state.OPEN:
                perms.add('new-proposal')
            if 'editor' in self.roles_for(user):
                perms.update(
                    (
                        'view_contactinfo',
                        'edit_project',
                        'delete-project',
                        'confirm-proposal',
                        'view-venue',
                        'new-venue',
                        'edit-venue',
                        'delete-venue',
                        'edit-schedule',
                        'move-proposal',
                        'view_rsvps',
                        'new-session',
                        'edit-session',
                        'new-event',
                        'new-ticket-type',
                        'new_ticket_client',
                        'edit_ticket_client',
                        'delete_ticket_client',
                        'edit_event',
                        'delete_event',
                        'admin',
                        'checkin_event',
                        'view-event',
                        'view_ticket_type',
                        'delete_ticket_type',
                        'edit-participant',
                        'view-participant',
                        'new-participant',
                        'view_contactinfo',
                        'confirm-proposal',
                        'view_voteinfo',
                        'view_status',
                        'delete-proposal',
                        'edit-schedule',
                        'new-session',
                        'edit-session',
                        'view-event',
                        'view_ticket_type',
                        'edit-participant',
                        'view-participant',
                        'new-participant',
                    )
                )
            if 'usher' in self.roles_for(user):
                perms.add('checkin_event')
        return perms

    @classmethod
    def all_unsorted(cls, legacy=None):
        """
        Return currently active events, not sorted.
        """
        projects = cls.query.filter(cls.state.PUBLISHED)
        if legacy is not None:
            projects = projects.join(Profile).filter(Profile.legacy == legacy)
        return projects

    @classmethod  # NOQA: A003
    def all(cls, legacy=None):  # NOQA: A003
        """
        Return currently active events, sorted by date.
        """
        return cls.all_unsorted(legacy).order_by(cls.schedule_start_at.desc())

    @classmethod
    def fetch_sorted(cls, legacy=None):
        currently_listed_projects = cls.query.filter_by(parent_project=None).filter(
            cls.state.PUBLISHED
        )
        if legacy is not None:
            currently_listed_projects = currently_listed_projects.join(Profile).filter(
                Profile.legacy == legacy
            )
        currently_listed_projects = currently_listed_projects.order_by(
            cls.schedule_start_at.desc()
        )
        return currently_listed_projects

    def roles_for(self, actor=None, anchors=()):
        roles = super().roles_for(actor, anchors)
        # https://github.com/hasgeek/funnel/pull/220#discussion_r168718052
        roles.add('reader')

        if actor is not None:
            profile_roles = self.profile.roles_for(actor, anchors)
            if 'admin' in profile_roles:
                roles.add('profile_admin')

            crew_membership = self.active_crew_memberships.filter_by(
                user=actor
            ).one_or_none()
            if crew_membership is not None:
                roles.update(crew_membership.offered_roles())

        return roles

    def is_saved_by(self, user):
        return (
            user is not None and self.saved_by.filter_by(user=user).first() is not None
        )


add_search_trigger(Project, 'search_vector')


Profile.listed_projects = db.relationship(
    Project,
    lazy='dynamic',
    primaryjoin=db.and_(
        Profile.id == Project.profile_id,
        Project.parent_id.is_(None),
        Project.state.PUBLISHED,
    ),
)


Profile.draft_projects = db.relationship(
    Project,
    lazy='dynamic',
    primaryjoin=db.and_(
        Profile.id == Project.profile_id,
        # TODO: parent projects are deprecated
        Project.parent_id.is_(None),
        db.or_(Project.state.DRAFT, Project.cfp_state.DRAFT),
    ),
)


Profile.draft_projects_for = (
    lambda self, user: (
        membership.project
        for membership in user.projects_as_crew_active_memberships.join(
            Project, Profile
        ).filter(
            # Project is attached to this profile
            Project.profile_id == self.id,
            # Project is not a sub-project (TODO: Deprecated, remove this)
            Project.parent_id.is_(None),
            # Project is in draft state OR has a draft call for proposals
            db.or_(Project.state.DRAFT, Project.cfp_state.DRAFT),
        )
    )
    if user
    else ()
)


class ProjectRedirect(TimestampMixin, db.Model):
    __tablename__ = "project_redirect"

    profile_id = db.Column(
        None, db.ForeignKey('profile.id'), nullable=False, primary_key=True
    )
    profile = db.relationship(
        'Profile', backref=db.backref('project_redirects', cascade='all')
    )
    parent = db.synonym('profile')
    name = db.Column(db.Unicode(250), nullable=False, primary_key=True)

    project_id = db.Column(
        None, db.ForeignKey('project.id', ondelete='SET NULL'), nullable=True
    )
    project = db.relationship(Project, backref='redirects')

    def __repr__(self):
        return '<ProjectRedirect %s/%s: %s>' % (
            self.profile.name,
            self.name,
            self.project.name if self.project else "(none)",
        )

    def redirect_view_args(self):
        if self.project:
            return {'profile': self.profile.name, 'project': self.project.name}
        else:
            return {}

    @classmethod
    def migrate_profile(cls, old_profile, new_profile):
        """
        There's no point trying to migrate redirects when merging profiles,`
        so discard them.
        """
        names = {pr.name for pr in new_profile.project_redirects}
        for pr in old_profile.project_redirects:
            if pr.name not in names:
                pr.profile = new_profile
            else:
                # Discard project redirect since the name is already taken by another
                # redirect in the new profile
                db.session.delete(pr)


class ProjectLocation(TimestampMixin, db.Model):
    __tablename__ = 'project_location'
    #: Project we are tagging
    project_id = db.Column(
        None, db.ForeignKey('project.id'), primary_key=True, nullable=False
    )
    project = db.relationship(Project, backref=db.backref('locations', cascade='all'))
    #: Geonameid for this project
    geonameid = db.Column(db.Integer, primary_key=True, nullable=False, index=True)
    primary = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return '<ProjectLocation %d %s for project %s>' % (
            self.geonameid,
            'primary' if self.primary else 'secondary',
            self.project,
        )


# Tail imports
from .session import Session  # isort:skip
from .venue import VenueRoom  # isort:skip
from .project_membership import ProjectCrewMembership  # isort:skip
