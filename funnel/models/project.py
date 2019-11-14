# -*- coding: utf-8 -*-

from collections import OrderedDict, defaultdict
from datetime import timedelta

from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy_utils import TimezoneType

from werkzeug.utils import cached_property

from babel.dates import format_date
from isoweek import Week
from pytz import utc

from baseframe import __, get_locale
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum, utcnow, valid_username

from ..util import geonameid_from_location
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
from .user import Team, User

__all__ = ['Project', 'ProjectLocation', 'ProjectRedirect']


# --- Constants ---------------------------------------------------------------


class PROJECT_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __(u"Draft"))
    PUBLISHED = (1, 'published', __(u"Published"))
    WITHDRAWN = (2, 'withdrawn', __(u"Withdrawn"))
    DELETED = (3, 'deleted', __("Deleted"))
    DELETABLE = {DRAFT, PUBLISHED, WITHDRAWN}
    PUBLISHABLE = {DRAFT, WITHDRAWN}


class CFP_STATE(LabeledEnum):  # NOQA: N801
    NONE = (0, 'none', __(u"None"))
    PUBLIC = (1, 'public', __(u"Public"))
    CLOSED = (2, 'closed', __(u"Closed"))
    OPENABLE = {NONE, CLOSED}
    EXISTS = {PUBLIC, CLOSED}


class SCHEDULE_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __(u"Draft"))
    PUBLISHED = (1, 'published', __(u"Published"))


# --- Models ------------------------------------------------------------------


class Project(UuidMixin, BaseScopedNameMixin, db.Model):
    __tablename__ = 'project'
    reserved_names = RESERVED_NAMES

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('projects', cascade='all, delete-orphan'),
    )
    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False)
    profile = db.relationship(
        'Profile',
        backref=db.backref('projects', cascade='all, delete-orphan', lazy='dynamic'),
    )
    parent = db.synonym('profile')
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = MarkdownColumn('description', default=u'', nullable=False)
    instructions = MarkdownColumn('instructions', default=u'', nullable=True)

    location = db.Column(db.Unicode(50), default=u'', nullable=True)
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

    admin_team_id = db.Column(
        None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True
    )
    admin_team = db.relationship(Team, foreign_keys=[admin_team_id])

    review_team_id = db.Column(
        None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True
    )
    review_team = db.relationship(Team, foreign_keys=[review_team_id])

    checkin_team_id = db.Column(
        None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True
    )
    checkin_team = db.relationship(Team, foreign_keys=[checkin_team_id])

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

    venues = db.relationship(
        'Venue',
        cascade='all, delete-orphan',
        order_by='Venue.seq',
        collection_class=ordering_list('seq', count_from=1),
    )
    labels = db.relationship(
        'Label',
        cascade='all, delete-orphan',
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
                'calendar_weeks',
                'primary_venue',
            },
            'call': {'url_for', 'current_sessions'},
        }
    }

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        self.voteset = Voteset(settype=SET_TYPE.PROJECT)
        self.commentset = Commentset(settype=SET_TYPE.PROJECT)

    def __repr__(self):
        return '<Project %s/%s "%s">' % (
            self.profile.name if self.profile else "(none)",
            self.name,
            self.title,
        )

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
        daterange = u""
        if self.schedule_start_at is not None and self.schedule_end_at is not None:
            schedule_start_at_date = self.schedule_start_at.astimezone(
                self.timezone
            ).date()
            schedule_end_at_date = self.schedule_end_at.astimezone(self.timezone).date()
            daterange_format = u"{start_date}–{end_date} {year}"
            if schedule_start_at_date == schedule_end_at_date:
                # if both dates are same, in case of single day project
                strf_date = ""
                daterange_format = u"{end_date} {year}"
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
        return u', '.join(filter(None, [daterange, self.location]))

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

    @with_roles(call={'admin'})
    @cfp_state.transition(
        cfp_state.OPENABLE,
        cfp_state.PUBLIC,
        title=__("Open CfP"),
        message=__("The call for proposals is now open"),
        type='success',
    )
    def open_cfp(self):
        pass

    @with_roles(call={'admin'})
    @cfp_state.transition(
        cfp_state.PUBLIC,
        cfp_state.CLOSED,
        title=__("Close CFP"),
        message=__("The call for proposals is now closed"),
        type='success',
    )
    def close_cfp(self):
        pass

    @with_roles(call={'admin'})
    @schedule_state.transition(
        schedule_state.DRAFT,
        schedule_state.PUBLISHED,
        title=__("Publish schedule"),
        message=__("The schedule has been published"),
        type='success',
    )
    def publish_schedule(self):
        pass

    @with_roles(call={'admin'})
    @schedule_state.transition(
        schedule_state.PUBLISHED,
        schedule_state.DRAFT,
        title=__("Unpublish schedule"),
        message=__("The schedule has been moved to draft state"),
        type='success',
    )
    def unpublish_schedule(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.PUBLISHABLE,
        state.PUBLISHED,
        title=__("Publish project"),
        message=__("The project has been published"),
        type='success',
    )
    def publish(self):
        pass

    @with_roles(call={'admin'})
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
    # @with_roles(call={'admin'})
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
        value = unicode(value).strip() if value is not None else None
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

    @cached_property
    def calendar_weeks(self):
        session_dates = list(
            db.session.query('date', 'count')
            .from_statement(
                db.text(
                    '''
                    SELECT DATE_TRUNC('day', "start_at" AT TIME ZONE :timezone) AS date, COUNT(*) AS count
                    FROM "session" WHERE "project_id" = :project_id AND "start_at" IS NOT NULL AND "end_at" IS NOT NULL
                    GROUP BY date ORDER BY date;
                    '''
                )
            )
            .params(timezone=self.timezone.zone, project_id=self.id)
        )

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

        if self.schedule_start_at is not None:
            current_week = Week.withdate(now)
            schedule_start_week = Week.withdate(self.schedule_start_at)

            if (
                schedule_start_week > current_week
                and (schedule_start_week - current_week) <= 2
            ):
                if (schedule_start_week - current_week) == 2:
                    session_dates.insert(0, (now + timedelta(days=7), 0))
                session_dates.insert(0, (now, 0))

        weeks = defaultdict(dict)
        for project_date, session_count in session_dates:
            weekobj = Week.withdate(project_date)
            if weekobj.week not in weeks:
                weeks[weekobj.week]['year'] = weekobj.year
                # Order is important, and we need dict to count easily
                weeks[weekobj.week]['dates'] = OrderedDict()
            for wdate in weekobj.days():
                weeks[weekobj.week]['dates'].setdefault(wdate, 0)
                if project_date.date() == wdate:
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
                }
                for date, count in week['dates'].items()
            ]

        return {
            'locale': get_locale(),
            'weeks': weeks_list,
            'today': now.date().isoformat(),
            'days': [
                format_date(day, 'EEEEE', locale=get_locale())
                for day in Week.thisweek().days()
            ],
        }

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
            if (
                (self.admin_team and user in self.admin_team.users)
                or (self.profile.admin_team and user in self.profile.admin_team.users)
                or user.owner_of(self.profile)
            ):
                perms.update(
                    [
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
                        'edit_event',
                        'admin',
                        'checkin_event',
                        'view-event',
                        'view_ticket_type',
                        'edit-participant',
                        'view-participant',
                        'new-participant',
                    ]
                )
            if self.review_team and user in self.review_team.users:
                perms.update(
                    [
                        'view_contactinfo',
                        'confirm-proposal',
                        'view_voteinfo',
                        'view_status',
                        'edit_proposal',
                        'delete-proposal',
                        'edit-schedule',
                        'new-session',
                        'edit-session',
                        'view-event',
                        'view_ticket_type',
                        'edit-participant',
                        'view-participant',
                        'new-participant',
                    ]
                )
            if self.checkin_team and user in self.checkin_team.users:
                perms.update(['checkin_event'])
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
    def all(cls, legacy=None):
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
        roles = super(Project, self).roles_for(actor, anchors)
        if actor is not None:
            if self.admin_team in actor.teams:
                roles.add('admin')
            if self.review_team in actor.teams:
                roles.add('reviewer')
            roles.add(
                'reader'
            )  # https://github.com/hasgeek/funnel/pull/220#discussion_r168718052
        roles.update(self.profile.roles_for(actor, anchors))
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
        Project.parent_id.is_(None),
        db.or_(Project.state.DRAFT, Project.cfp_state.DRAFT),
    ),
)


class ProjectRedirect(TimestampMixin, db.Model):
    __tablename__ = "project_redirect"

    profile_id = db.Column(
        None, db.ForeignKey('profile.id'), nullable=False, primary_key=True
    )
    profile = db.relationship(
        'Profile', backref=db.backref('project_redirects', cascade='all, delete-orphan')
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
    def migrate_profile(cls, oldprofile, newprofile):
        """
        There's no point trying to migrate redirects when merging profiles, so discard them.
        """
        oldprofile.project_redirects = []
        return [cls.__table__.name]


class ProjectLocation(TimestampMixin, db.Model):
    __tablename__ = 'project_location'
    #: Project we are tagging
    project_id = db.Column(
        None, db.ForeignKey('project.id'), primary_key=True, nullable=False
    )
    project = db.relationship(
        Project, backref=db.backref('locations', cascade='all, delete-orphan')
    )
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
