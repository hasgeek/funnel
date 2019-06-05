# -*- coding: utf-8 -*-

from werkzeug.utils import cached_property
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy_utils import TimezoneType
from pytz import utc

from baseframe import __

from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum, utcnow

from ..util import geonameid_from_location
from . import BaseScopedNameMixin, JsonDict, MarkdownColumn, TimestampMixin, UuidMixin, UrlType, db
from .user import Team, User
from .profile import Profile
from .commentvote import Commentset, SET_TYPE, Voteset
from .helper import RESERVED_NAMES

__all__ = ['Project', 'ProjectRedirect', 'ProjectLocation']


# --- Constants ---------------------------------------------------------------

class PROJECT_STATE(LabeledEnum):
    DRAFT = (0, 'draft', __(u"Draft"))
    PUBLISHED = (1, 'published', __(u"Published"))
    WITHDRAWN = (2, 'withdrawn', __(u"Withdrawn"))
    DELETED = (3, 'deleted', __("Deleted"))
    DELETABLE = {DRAFT, PUBLISHED, WITHDRAWN}
    PUBLISHABLE = {DRAFT, WITHDRAWN}


class CFP_STATE(LabeledEnum):
    NONE = (0, 'none', __(u"None"))
    PUBLIC = (1, 'public', __(u"Public"))
    CLOSED = (2, 'closed', __(u"Closed"))
    OPENABLE = {NONE, CLOSED}
    EXISTS = {PUBLIC, CLOSED}


class SCHEDULE_STATE(LabeledEnum):
    DRAFT = (0, 'draft', __(u"Draft"))
    PUBLISHED = (1, 'published', __(u"Published"))


# --- Models ------------------------------------------------------------------

class Project(UuidMixin, BaseScopedNameMixin, db.Model):
    __tablename__ = 'project'
    reserved_names = RESERVED_NAMES

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        User, primaryjoin=user_id == User.id,
        backref=db.backref('projects', cascade='all, delete-orphan'))
    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False)
    profile = db.relationship('Profile', backref=db.backref('projects', cascade='all, delete-orphan', lazy='dynamic'))
    parent = db.synonym('profile')
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = MarkdownColumn('description', default=u'', nullable=False)
    instructions = MarkdownColumn('instructions', default=u'', nullable=True)

    location = db.Column(db.Unicode(50), default=u'', nullable=True)
    parsed_location = db.Column(JsonDict, nullable=False, server_default='{}')

    date = db.Column(db.Date, nullable=True)
    date_upto = db.Column(db.Date, nullable=True)

    website = db.Column(UrlType, nullable=True)
    timezone = db.Column(TimezoneType(backend='pytz'), nullable=False, default=utc)

    _state = db.Column(
        'state',
        db.Integer,
        StateManager.check_constraint('state', PROJECT_STATE),
        default=PROJECT_STATE.DRAFT,
        nullable=False)
    state = StateManager('_state', PROJECT_STATE, doc="Project state")
    _cfp_state = db.Column(
        'cfp_state',
        db.Integer,
        StateManager.check_constraint('cfp_state', CFP_STATE),
        default=CFP_STATE.NONE,
        nullable=False)
    cfp_state = StateManager('_cfp_state', CFP_STATE, doc="CfP state")
    _schedule_state = db.Column(
        'schedule_state',
        db.Integer,
        StateManager.check_constraint('schedule_state', SCHEDULE_STATE),
        default=SCHEDULE_STATE.DRAFT,
        nullable=False)
    schedule_state = StateManager('_schedule_state', SCHEDULE_STATE, doc="Schedule state")

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

    admin_team_id = db.Column(None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True)
    admin_team = db.relationship(Team, foreign_keys=[admin_team_id])

    review_team_id = db.Column(None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True)
    review_team = db.relationship(Team, foreign_keys=[review_team_id])

    checkin_team_id = db.Column(None, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True)
    checkin_team = db.relationship(Team, foreign_keys=[checkin_team_id])

    parent_id = db.Column(None, db.ForeignKey('project.id', ondelete='SET NULL'), nullable=True)
    parent_project = db.relationship('Project', remote_side='Project.id', backref='subprojects')
    inherit_sections = db.Column(db.Boolean, default=True, nullable=False)
    part_labels = db.Column('labels', JsonDict, nullable=False, server_default='{}')

    #: Featured project flag. This can only be set by website editors, not
    #: project editors or profile admins.
    featured = db.Column(db.Boolean, default=False, nullable=False)

    venues = db.relationship('Venue', cascade='all, delete-orphan',
        order_by='Venue.seq', collection_class=ordering_list('seq', count_from=1))
    labels = db.relationship('Label', cascade='all, delete-orphan',
        primaryjoin='and_(Label.project_id == Project.id, Label.main_label_id == None, Label._archived == False)',
        order_by='Label.seq', collection_class=ordering_list('seq', count_from=1))
    all_labels = db.relationship('Label', lazy='dynamic')

    featured_sessions = db.relationship(
        'Session',
        primaryjoin='and_(Session.project_id == Project.id, Session.featured == True)')
    scheduled_sessions = db.relationship(
        'Session',
        primaryjoin='and_(Session.project_id == Project.id, Session.scheduled)')
    unscheduled_sessions = db.relationship(
        'Session',
        primaryjoin='and_(Session.project_id == Project.id, Session.scheduled != True)')

    __table_args__ = (db.UniqueConstraint('profile_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'id', 'name', 'title', 'datelocation', 'timezone', 'date', 'date_upto', 'url_json',
                '_state', 'website', 'bg_image', 'bg_color', 'explore_url', 'tagline', 'absolute_url',
                'location'
                },
            }
        }

    @cached_property
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

        ``datelocation_format`` always keeps ``date_upto`` format as ``–DD Mmm YYYY``.
        Depending on the scenario mentioned below, format for ``date`` changes. Above examples
        demonstrate the same. All the possible outputs end with ``–DD Mmm YYYY, Venue``.
        Only ``date`` format changes.
        """
        datelocation_format = u"{date}–{date_upto} {year}"
        if self.date == self.date_upto:
            # if both dates are same, in case of single day project
            strf_date = ""
            datelocation_format = u"{date_upto} {year}"
        elif self.date.month == self.date_upto.month:
            # If multi-day event in same month
            strf_date = "%d"
        elif self.date.month != self.date_upto.month:
            # If multi-day event across months
            strf_date = "%d %b"
        elif self.date.year != self.date_upto.year:
            # if the start date and end dates are in different years,
            strf_date = "%d %b %Y"
        datelocation = datelocation_format.format(
            date=self.date.strftime(strf_date),
            date_upto=self.date_upto.strftime("%d %b"),
            year=self.date.year)
        return datelocation if not self.location else u', '.join([datelocation, self.location])

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        self.voteset = Voteset(type=SET_TYPE.PROJECT)
        self.commentset = Commentset(type=SET_TYPE.PROJECT)

    def __repr__(self):
        return '<Project %s/%s "%s">' % (self.profile.name if self.profile else "(none)", self.name, self.title)

    state.add_conditional_state('PAST', state.PUBLISHED,
        lambda project: project.date_upto is not None and project.date_upto < utcnow().date(),
        label=('past', __("Past")))
    state.add_conditional_state('UPCOMING', state.PUBLISHED,
        lambda project: project.date_upto is not None and project.date_upto >= utcnow().date(),
        label=('upcoming', __("Upcoming")))

    cfp_state.add_conditional_state('HAS_PROPOSALS', cfp_state.EXISTS,
        lambda project: db.session.query(project.proposals.exists()).scalar(),
        label=('has_proposals', __("Has Proposals")))
    cfp_state.add_conditional_state('HAS_SESSIONS', cfp_state.EXISTS,
        lambda project: db.session.query(project.sessions.exists()).scalar(),
        label=('has_sessions', __("Has Sessions")))
    cfp_state.add_conditional_state('PRIVATE_DRAFT', cfp_state.NONE,
        lambda project: project.instructions.html != '',
        lambda project: project.__table__.c.instructions_html != '',
        label=('private_draft', __("Private draft")))
    cfp_state.add_conditional_state('DRAFT', cfp_state.PUBLIC,
        lambda project: project.cfp_start_at is None,
        lambda project: project.__table__.c.cfp_start_at == None,  # NOQA
        label=('draft', __("Draft")))
    cfp_state.add_conditional_state('UPCOMING', cfp_state.PUBLIC,
        lambda project: project.cfp_start_at is not None and project.cfp_start_at > utcnow(),
        lambda project: db.and_(project.cfp_start_at is not None, project.cfp_start_at > db.func.utcnow()),
        label=('upcoming', __("Upcoming")))
    cfp_state.add_conditional_state('OPEN', cfp_state.PUBLIC,
        lambda project: project.cfp_start_at is not None and project.cfp_start_at <= utcnow() and (
            project.cfp_end_at is None or project.cfp_end_at > utcnow()),
        lambda project: db.and_(project.cfp_start_at is not None and project.cfp_start_at <= db.func.utcnow(), (
            project.cfp_end_at is None or project.cfp_end_at > db.func.utcnow())),
        label=('open', __("Open")))
    cfp_state.add_conditional_state('EXPIRED', cfp_state.PUBLIC,
        lambda project: project.cfp_end_at is not None and project.cfp_end_at <= utcnow(),
        lambda project: db.and_(project.cfp_end_at is not None, project.cfp_end_at <= db.func.utcnow()),
        label=('expired', __("Expired")))

    @with_roles(call={'admin'})
    @cfp_state.transition(
        cfp_state.OPENABLE, cfp_state.PUBLIC, title=__("Open CfP"),
        message=__("The call for proposals is now open"), type='success')
    def open_cfp(self):
        pass

    @with_roles(call={'admin'})
    @cfp_state.transition(
        cfp_state.PUBLIC, cfp_state.CLOSED, title=__("Close CFP"),
        message=__("The call for proposals is now closed"), type='success')
    def close_cfp(self):
        pass

    @with_roles(call={'admin'})
    @schedule_state.transition(
        schedule_state.DRAFT, schedule_state.PUBLISHED, title=__("Publish schedule"),
        message=__("The schedule has been published"), type='success')
    def publish_schedule(self):
        pass

    @with_roles(call={'admin'})
    @schedule_state.transition(
        schedule_state.PUBLISHED, schedule_state.DRAFT, title=__("Unpublish schedule"),
        message=__("The schedule has been moved to draft state"), type='success')
    def unpublish_schedule(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.PUBLISHABLE, state.PUBLISHED, title=__("Publish project"),
        message=__("The project has been published"), type='success')
    def publish(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.PUBLISHED, state.WITHDRAWN, title=__("Withdraw project"),
        message=__("The project has been withdrawn and is no longer listed"), type='success')
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
        if not value:
            raise ValueError(value)

        if value != self.name and self.name is not None and self.profile is not None:
            redirect = ProjectRedirect.query.get((self.profile_id, self.name))
            if redirect is None:
                redirect = ProjectRedirect(profile=self.profile, name=self.name, project=self)
                db.session.add(redirect)
            else:
                redirect.project = self
        return value

    @property
    def rooms(self):
        return [room for venue in self.venues for room in venue.rooms]

    @property
    def proposals_all(self):
        from .proposal import Proposal
        if self.subprojects:
            return Proposal.query.filter(Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects]))
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
            basequery.filter(~Proposal.state.DRAFT).order_by(db.desc('created_at'))
            )

    @property
    def proposals_by_confirmation(self):
        from .proposal import Proposal
        if self.subprojects:
            basequery = Proposal.query.filter(Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects]))
        else:
            basequery = Proposal.query.filter_by(project=self)
        return dict(
            confirmed=basequery.filter(Proposal.state.CONFIRMED).order_by(db.desc('created_at')).all(),
            unconfirmed=basequery.filter(~Proposal.state.CONFIRMED, ~Proposal.state.DRAFT).order_by(
                db.desc('created_at')).all())

    @cached_property
    def location_geonameid(self):
        return geonameid_from_location(self.location) if self.location else set()

    @property
    def proposal_part_a(self):
        return self.part_labels.get('proposal', {}).get('part_a', {})

    @property
    def proposal_part_b(self):
        return self.part_labels.get('proposal', {}).get('part_b', {})

    def set_labels(self, value=None):
        """
        Sets 'labels' with the provided JSON, else with a default configuration
        for fields with customizable labels.

        Currently, the 'part_a' and 'part_b' fields in 'Proposal'
        are allowed to be customized per project.
        """
        if value and isinstance(value, dict):
            self.part_labels = value
        else:
            self.part_labels = {
                "proposal": {
                    "part_a": {
                        "title": "Abstract",
                        "hint": "Give us a brief description of your talk, key takeaways for the audience and the"
                        " intended audience."
                        },
                    "part_b": {
                        "title": "Outline",
                        "hint": "Give us a break-up of your talk either in the form of draft slides, mind-map or"
                        " text description."
                        }
                    }
                }

    def permissions(self, user, inherited=None):
        perms = super(Project, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            if self.cfp_state.OPEN:
                perms.add('new-proposal')
            if ((self.admin_team and user in self.admin_team.users)
                or (self.profile.admin_team and user in self.profile.admin_team.users)
                    or user.owner_of(self.profile)):
                perms.update([
                    'view_contactinfo',
                    'edit_project',
                    'delete-project',
                    'view-section',
                    'new-section',
                    'edit-section',
                    'delete-section',
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
                    'new-ticket-client',
                    'edit-ticket-client',
                    'edit-event',
                    'admin',
                    'checkin_event',
                    'view-event',
                    'view-ticket-type',
                    'edit-participant',
                    'view-participant',
                    'new-participant',
                    ])
            if self.review_team and user in self.review_team.users:
                perms.update([
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
                    'view-ticket-type',
                    'edit-participant',
                    'view-participant',
                    'new-participant'
                    ])
            if self.checkin_team and user in self.checkin_team.users:
                perms.update([
                    'checkin_event'
                    ])
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

    @classmethod
    def all(cls, legacy=None):
        """
        Return currently active events, sorted by date.
        """
        return cls.all_unsorted(legacy).order_by(cls.date.desc())

    @classmethod
    def fetch_sorted(cls, legacy=None):
        currently_listed_projects = cls.query.filter_by(parent_project=None).filter(cls.state.PUBLISHED)
        if legacy is not None:
            currently_listed_projects = currently_listed_projects.join(Profile).filter(Profile.legacy == legacy)
        currently_listed_projects = currently_listed_projects.order_by(cls.date.desc())
        return currently_listed_projects

    def roles_for(self, actor=None, anchors=()):
        roles = super(Project, self).roles_for(actor, anchors)
        if actor is not None:
            if self.admin_team in actor.teams:
                roles.add('admin')
            if self.review_team in actor.teams:
                roles.add('reviewer')
            roles.add('reader')  # https://github.com/hasgeek/funnel/pull/220#discussion_r168718052
        roles.update(self.profile.roles_for(actor, anchors))
        return roles


Profile.listed_projects = db.relationship(
        Project, lazy='dynamic',
        primaryjoin=db.and_(
            Profile.id == Project.profile_id, Project.parent_id == None,
            Project.state.PUBLISHED),
        order_by=Project.date.desc())  # NOQA


Profile.draft_projects = db.relationship(
        Project, lazy='dynamic',
        primaryjoin=db.and_(
            Profile.id == Project.profile_id, Project.parent_id == None,
            db.or_(Project.state.DRAFT, Project.cfp_state.DRAFT)),
        order_by=Project.date.desc())  # NOQA


class ProjectRedirect(TimestampMixin, db.Model):
    __tablename__ = "project_redirect"

    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False, primary_key=True)
    profile = db.relationship('Profile', backref=db.backref('project_redirects', cascade='all, delete-orphan'))
    parent = db.synonym('profile')
    name = db.Column(db.Unicode(250), nullable=False, primary_key=True)

    project_id = db.Column(None, db.ForeignKey('project.id', ondelete='SET NULL'), nullable=True)
    project = db.relationship(Project, backref='redirects')

    def __repr__(self):
        return '<ProjectRedirect %s/%s: %s>' % (
            self.profile.name, self.name,
            self.project.name if self.project else "(none)")

    def redirect_view_args(self):
        if self.project:
            return {
                'profile': self.profile.name,
                'project': self.project.name}
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
    project_id = db.Column(None, db.ForeignKey('project.id'), primary_key=True, nullable=False)
    project = db.relationship(Project, backref=db.backref('locations', cascade='all, delete-orphan'))
    #: Geonameid for this project
    geonameid = db.Column(db.Integer, primary_key=True, nullable=False, index=True)
    primary = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return '<ProjectLocation %d %s for project %s>' % (
            self.geonameid, 'primary' if self.primary else 'secondary', self.project)
