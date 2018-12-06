# -*- coding: utf-8 -*-

from werkzeug.utils import cached_property

from flask import url_for

from baseframe import __

from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from ..util import geonameid_from_location
from . import BaseScopedNameMixin, JsonDict, MarkdownColumn, TimestampMixin, db
from .user import Team, User
from .commentvote import Commentset, SET_TYPE, Voteset

__all__ = ['Project', 'ProjectRedirect', 'ProjectLocation']


# --- Constants ---------------------------------------------------------------

class PROJECT_STATE(LabeledEnum):  # NOQA
    # If you add any new state, you need to add a migration to modify the check constraint
    DRAFT = (0, 'draft', __(u"Draft"))
    SUBMISSIONS = (1, 'submissions', __(u"Accepting submissions"))
    VOTING = (2, 'voting', __(u"Accepting votes"))
    FEEDBACK = (4, 'feedback', __(u"Open for feedback"))
    CLOSED = (5, 'closed', __(u"Closed"))
    # Jury state are not in the editorial workflow anymore - Feb 24 2018
    WITHDRAWN = (6, 'withdrawn', __(u"Withdrawn"))
    JURY = (3, 'jury', __(u"Awaiting jury selection"))

    CURRENTLY_LISTED = {SUBMISSIONS, VOTING, JURY, FEEDBACK}
    OPENABLE = {VOTING, FEEDBACK, CLOSED, WITHDRAWN, JURY}


# --- Models ------------------------------------------------------------------

class Project(BaseScopedNameMixin, db.Model):
    __tablename__ = 'project'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        User, primaryjoin=user_id == User.id,
        backref=db.backref('projects', cascade='all, delete-orphan'))
    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False)
    profile = db.relationship('Profile', backref=db.backref('projects', cascade='all, delete-orphan'))
    parent = db.synonym('profile')
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = MarkdownColumn('description', default=u'', nullable=False)
    instructions = MarkdownColumn('instructions', default=u'', nullable=True)

    location = db.Column(db.Unicode(50), default=u'', nullable=True)
    parsed_location = db.Column(JsonDict, nullable=False, server_default='{}')

    date = db.Column(db.Date, nullable=True)
    date_upto = db.Column(db.Date, nullable=True)

    website = db.Column(db.Unicode(2000), nullable=True)
    timezone = db.Column(db.Unicode(40), nullable=False, default=u'UTC')

    _state = db.Column(
        'state', db.Integer, StateManager.check_constraint('state', PROJECT_STATE),
        default=PROJECT_STATE.DRAFT, nullable=False)
    state = StateManager('_state', PROJECT_STATE, doc="State of this project.")

    # Columns for mobile
    bg_image = db.Column(db.Unicode(2000), nullable=True)
    bg_color = db.Column(db.Unicode(6), nullable=True)
    explore_url = db.Column(db.Unicode(2000), nullable=True)
    allow_rsvp = db.Column(db.Boolean, default=False, nullable=False)
    buy_tickets_url = db.Column(db.Unicode(2000), nullable=True)

    banner_video_url = db.Column(db.Unicode(2000), nullable=True)
    boxoffice_data = db.Column(JsonDict, nullable=False, server_default='{}')

    hasjob_embed_url = db.Column(db.Unicode(2000), nullable=True)
    hasjob_embed_limit = db.Column(db.Integer, default=8)

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(Commentset, uselist=False)

    admin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    admin_team = db.relationship(Team, foreign_keys=[admin_team_id])

    review_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    review_team = db.relationship(Team, foreign_keys=[review_team_id])

    checkin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    checkin_team = db.relationship(Team, foreign_keys=[checkin_team_id])

    parent_id = db.Column(None, db.ForeignKey('project.id', ondelete='SET NULL'), nullable=True)
    parent = db.relationship('Project', remote_side='Project.id', backref='subprojects')
    inherit_sections = db.Column(db.Boolean, default=True, nullable=False)
    labels = db.Column(JsonDict, nullable=False, server_default='{}')

    featured_sessions = db.relationship(
        'Session',
        primaryjoin='and_(Session.project_id == Project.id, Session.featured == True)')
    scheduled_sessions = db.relationship(
        'Session',
        primaryjoin='and_(Session.project_id == Project.id, Session.scheduled)')
    unscheduled_sessions = db.relationship(
        'Session',
        primaryjoin='and_(Session.project_id == Project.id, Session.scheduled != True)')

    #: Redirect URLs from Funnel to Talkfunnel
    legacy_name = db.Column(db.Unicode(250), nullable=True, unique=True)

    __table_args__ = (db.UniqueConstraint('profile_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'id', 'name', 'title', 'datelocation', 'timezone', 'date', 'date_upto', 'url_json',
                '_state', 'website', 'bg_image', 'bg_color', 'explore_url', 'tagline', 'url',
                'location'
            },
        },
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

    @property
    def url(self):
        return self.url_for(_external=True)

    @property
    def url_json(self):
        return self.url_for('json', _external=True)

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        self.voteset = Voteset(type=SET_TYPE.PROJECT)
        self.commentset = Commentset(type=SET_TYPE.PROJECT)

    def __repr__(self):
        return '<Project %s/%s "%s">' % (self.profile.name if self.profile else "(none)", self.name, self.title)

    @with_roles(call={'admin'})
    @state.transition(
        state.DRAFT, state.SUBMISSIONS, title=__("Open"),
        message=__("This project has been opened to accept submissions"), type='success')
    def accept_submissions(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.SUBMISSIONS, state.VOTING, title=__("Close submissions"),
        message=__("This project has now closed submissions, but is still accepting votes"), type='success')
    def accept_votes(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.VOTING, state.FEEDBACK, title=__("Close voting"),
        message=__("This project has now closed submissions and voting, but is still accepting feedback comments"),
        type='success')
    def accept_feedback(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.OPENABLE, state.SUBMISSIONS, title=__("Reopen Submissions"),
        message=__("This project has been reopened for submissions"), type='success')
    def reopen(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.CURRENTLY_LISTED, state.CLOSED, title=__("Close & Hide"),
        message=__("This project has been closed and will no longer be listed"), type='danger')
    def close(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(
        state.CLOSED, state.FEEDBACK, title=__("Relist"),
        message=__("This project has been relisted, but is only accepting feedback comments"), type='success')
    def relist(self):
        pass

    # TODO: Confirm with the media team whether they need to withdraw projects
    #
    # @with_roles(call={'admin'})
    # @state.transition(
    #     state.CLOSED, state.WITHDRAWN, title=__("Withdraw"),
    #     message=__("This project has been withdrawn"), type='success')
    # def withdraw(self):
    #     pass

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
        return self.labels.get('proposal', {}).get('part_a', {})

    @property
    def proposal_part_b(self):
        return self.labels.get('proposal', {}).get('part_b', {})

    def set_labels(self, value=None):
        """
        Sets 'labels' with the provided JSON, else with a default configuration
        for fields with customizable labels.

        Currently, the 'part_a' and 'part_b' fields in 'Proposal'
        are allowed to be customized per project.
        """
        if value and isinstance(value, dict):
            self.labels = value
        else:
            self.labels = {
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

    def user_in_group(self, user, group):
        for grp in self.usergroups:
            if grp.name == group:
                if user in grp.users:
                    return True
        return False

    def permissions(self, user, inherited=None):
        perms = super(Project, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            if self.state.SUBMISSIONS:
                perms.add('new-proposal')
            if ((self.admin_team and user in self.admin_team.users) or
                (self.profile.admin_team and user in self.profile.admin_team.users) or
                    user.owner_of(self.profile)):
                perms.update([
                    'view-contactinfo',
                    'edit-project',
                    'delete-project',
                    'view-section',
                    'new-section',
                    'edit-section',
                    'delete-section',
                    'view-usergroup',
                    'new-usergroup',
                    'edit-usergroup',
                    'delete-usergroup',
                    'confirm-proposal',
                    'view-venue',
                    'new-venue',
                    'edit-venue',
                    'delete-venue',
                    'edit-schedule',
                    'move-proposal',
                    'view-rsvps',
                    'new-session',
                    'edit-session',
                    'new-event',
                    'new-ticket-type',
                    'new-ticket-client',
                    'edit-ticket-client',
                    'edit-event',
                    'admin',
                    'checkin-event',
                    'view-event',
                    'view-ticket-type',
                    'edit-participant',
                    'view-participant',
                    'new-participant'
                ])
            if self.review_team and user in self.review_team.users:
                perms.update([
                    'view-contactinfo',
                    'confirm-proposal',
                    'view-voteinfo',
                    'view-status',
                    'edit-proposal',
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
                    'checkin-event'
                ])
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('project_view', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'new-proposal':
            return url_for('proposal_new', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'json':
            return url_for('project_view_json', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'csv':
            return url_for('project_view_csv', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'edit':
            return url_for('project_edit', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'transition':
            return url_for('project_transition', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'sections':
            return url_for('section_list', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'new-section':
            return url_for('section_new', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'usergroups':
            return url_for('usergroup_list', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'new-usergroup':
            return url_for('usergroup_new', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'venues':
            return url_for('venue_list', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'new-venue':
            return url_for('venue_new', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'schedule':
            return url_for('schedule_view', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'edit-schedule':
            return url_for('schedule_edit', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'update-schedule':
            return url_for('schedule_update', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'new-session':
            return url_for('session_new', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'update-venue-colors':
            return url_for('update_venue_colors', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'json-schedule':
            return url_for('schedule_json', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'subscribe-schedule':
            return url_for('schedule_subscribe', profile=self.profile.name, project=self.name, _external=_external)
        elif action == 'ical-schedule':
            return url_for('schedule_ical', profile=self.profile.name, project=self.name, _external=_external).replace(
                'https:', 'webcals:').replace('http:', 'webcal:')
        elif action == 'rsvp':
            return url_for('rsvp', profile=self.profile.name, project=self.name)
        elif action == 'rsvp-list':
            return url_for('rsvp_list', profile=self.profile.name, project=self.name)
        elif action == 'admin':
            return url_for('admin', profile=self.profile.name, project=self.name)
        elif action == 'events':
            return url_for('events', profile=self.profile.name, project=self.name)
        elif action == 'participants':
            return url_for('participants', profile=self.profile.name, project=self.name)
        elif action == 'new-participant':
            return url_for('new_participant', profile=self.profile.name, project=self.name)
        elif action == 'new-ticket-type-participant':
            return url_for('new_ticket_type_participant', profile=self.profile.name, project=self.name)
        elif action == 'new-event':
            return url_for('new_event', profile=self.profile.name, project=self.name)
        elif action == 'new-ticket-type':
            return url_for('new_ticket_type', profile=self.profile.name, project=self.name)
        elif action == 'new-ticket-client':
            return url_for('new_ticket_client', profile=self.profile.name, project=self.name)

    @classmethod
    def all(cls):
        """
        Return currently active events, sorted by date.
        """
        return cls.query.filter(cls.state.CURRENTLY_LISTED).order_by(cls.date.desc()).all()

    @classmethod
    def fetch_sorted(cls):
        # sorts the projects so that both new and old projects are sorted from closest to farthest
        now = db.func.utcnow()
        currently_listed_projects = cls.query.filter_by(parent=None).filter(
            cls.state.CURRENTLY_LISTED)
        upcoming = currently_listed_projects.filter(cls.date >= now).order_by(cls.date.asc())
        past = currently_listed_projects.filter(cls.date < now).order_by(cls.date.desc())

        # union_all() because union() doesn't respect the orders mentioned in subqueries
        return upcoming.union_all(past)

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
