# -*- coding: utf-8 -*-

from flask import url_for
from . import db, TimestampMixin, BaseScopedNameMixin, MarkdownColumn, JsonDict
from .user import User, Team
from .profile import Profile
from .commentvote import VoteSpace, CommentSpace, SPACETYPE
from werkzeug.utils import cached_property
from ..util import geonameid_from_location
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum
from baseframe import __

from collections import defaultdict

__all__ = ['ProposalSpace', 'ProposalSpaceRedirect']


# --- Constants ---------------------------------------------------------------

class SPACE_STATE(LabeledEnum):
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
    FEEDBACKABLE = {SUBMISSIONS, VOTING}
    VOTABLE = {SUBMISSIONS, JURY}


# --- Models ------------------------------------------------------------------

class ProposalSpace(BaseScopedNameMixin, db.Model):
    __tablename__ = 'proposal_space'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('spaces', cascade='all, delete-orphan'))
    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=True)  # nullable for transition
    profile = db.relationship(Profile, backref=db.backref('spaces', cascade='all, delete-orphan'))
    parent = db.synonym('profile')
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = MarkdownColumn('description', default=u'', nullable=False)
    instructions = MarkdownColumn('instructions', default=u'', nullable=True)
    datelocation = db.Column(db.Unicode(50), default=u'', nullable=False)
    date = db.Column(db.Date, nullable=True)
    date_upto = db.Column(db.Date, nullable=True)
    website = db.Column(db.Unicode(250), nullable=True)
    timezone = db.Column(db.Unicode(40), nullable=False, default=u'UTC')

    _state = db.Column('status', db.Integer, StateManager.check_constraint('status', SPACE_STATE),
        default=SPACE_STATE.DRAFT, nullable=False)
    state = StateManager('_state', SPACE_STATE, doc="State of this proposal space.")

    # Columns for mobile
    bg_image = db.Column(db.Unicode(250), nullable=True)
    bg_color = db.Column(db.Unicode(6), nullable=True)
    explore_url = db.Column(db.Unicode(250), nullable=True)
    allow_rsvp = db.Column(db.Boolean, default=False, nullable=False)
    buy_tickets_url = db.Column(db.Unicode(250), nullable=True)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    admin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    admin_team = db.relationship(Team, foreign_keys=[admin_team_id])

    review_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    review_team = db.relationship(Team, foreign_keys=[review_team_id])

    checkin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    checkin_team = db.relationship(Team, foreign_keys=[checkin_team_id])

    parent_space_id = db.Column(None, db.ForeignKey('proposal_space.id', ondelete='SET NULL'), nullable=True)
    parent_space = db.relationship('ProposalSpace', remote_side='ProposalSpace.id', backref='subspaces')
    inherit_sections = db.Column(db.Boolean, default=True, nullable=False)
    labels = db.Column(JsonDict, nullable=False, server_default='{}')

    #: Redirect URLs from Funnel to Talkfunnel
    legacy_name = db.Column(db.Unicode(250), nullable=True, unique=True)

    __table_args__ = (db.UniqueConstraint('profile_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'id', 'name', 'title', 'datelocation', 'timezone', 'date', 'date_upto', 'json_url',
                '_state', 'website', 'bg_image', 'bg_color', 'explore_url', 'tagline', 'url'
                },
            },
        }

    @property
    def url(self):
        return self.url_for(_external=True)

    @property
    def json_url(self):
        return self.url_for('json', _external=True)

    def __init__(self, **kwargs):
        super(ProposalSpace, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSALSPACE)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSALSPACE)

    def __repr__(self):
        return '<ProposalSpace %s/%s "%s">' % (self.profile.name if self.profile else "(none)", self.name, self.title)

    @with_roles(call={'admin'})
    @state.transition(state.DRAFT, state.SUBMISSIONS, title=__("Accept submissions"), message=__("This proposal space has been opened to accept submissions"), type='success')
    def accept_submissions(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.VOTABLE, state.VOTING, title=__("Accept votes"), message=__("This proposal space has been opened to accept votes"), type='success')
    def accept_votes(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.FEEDBACKABLE, state.FEEDBACK, title=__("Accept feedback"), message=__("This proposal space has been opened to accept feedback"), type='success')
    def accept_feedback(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.CURRENTLY_LISTED, state.CLOSED, title=__("Close"), message=__("This proposal space has been closed"), type='danger')
    def close(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.CLOSED, state.SUBMISSIONS, title=__("Reopen"), message=__("This proposal space has been reopened"), type='success')
    def reopen(self):
        pass

    # TODO: Confirm with the media team whether they need the withdraw proposal spaces
    #
    # @with_roles(call={'admin'})
    # @state.transition(state.CLOSED, state.WITHDRAWN, title=__("Withdraw"), message=__("This proposal space has been withdrawn"), type='success')
    # def withdraw(self):
    #     pass

    @db.validates('name')
    def _validate_name(self, key, value):
        value = unicode(value).strip() if value is not None else None
        if not value:
            raise ValueError(value)

        if value != self.name and self.name is not None and self.profile is not None:
            redirect = ProposalSpaceRedirect.query.get((self.profile_id, self.name))
            if redirect is None:
                redirect = ProposalSpaceRedirect(profile=self.profile, name=self.name, proposal_space=self)
                db.session.add(redirect)
            else:
                redirect.proposal_space = self
        return value

    @property
    def rooms(self):
        return [room for venue in self.venues for room in venue.rooms]

    @property
    def proposals_all(self):
        from .proposal import Proposal
        if self.subspaces:
            return Proposal.query.filter(Proposal.proposal_space_id.in_([self.id] + [s.id for s in self.subspaces]))
        else:
            return self.proposals

    @property
    def proposals_by_state(self):
        from .proposal import Proposal
        if self.subspaces:
            basequery = Proposal.query.filter(
                Proposal.proposal_space_id.in_([self.id] + [s.id for s in self.subspaces])
            )
        else:
            basequery = Proposal.query.filter_by(proposal_space=self)
        return Proposal.state.group(
            basequery.filter(~Proposal.state.DRAFT).order_by(db.desc('created_at'))
        )

    @property
    def proposals_by_confirmation(self):
        from .proposal import Proposal
        if self.subspaces:
            basequery = Proposal.query.filter(Proposal.proposal_space_id.in_([self.id] + [s.id for s in self.subspaces]))
        else:
            basequery = Proposal.query.filter_by(proposal_space=self)
        return dict(
            confirmed=basequery.filter(Proposal.state.CONFIRMED).order_by(db.desc('created_at')).all(),
            unconfirmed=basequery.filter(~Proposal.state.CONFIRMED, ~Proposal.state.DRAFT).order_by(db.desc('created_at')).all()
            )

    @cached_property
    def location_geonameid(self):
        return geonameid_from_location(self.datelocation)

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
        are allowed to be customized per proposal space.
        """
        if value and isinstance(value, dict):
            self.labels = value
        else:
            self.labels = {
                "proposal": {
                    "part_a": {
                        "title": "Abstract",
                        "hint": "Give us a brief description of your talk, key takeaways for the audience and the intended audience."
                    },
                    "part_b": {
                        "title": "Outline",
                        "hint": "Give us a break-up of your talk either in the form of draft slides, mind-map or text description."
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
        perms = super(ProposalSpace, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            if self.state.SUBMISSIONS:
                perms.add('new-proposal')
            if ((self.admin_team and user in self.admin_team.users) or
                (self.profile.admin_team and user in self.profile.admin_team.users) or
                    user.owner_of(self.profile)):
                perms.update([
                    'view-contactinfo',
                    'edit-space',
                    'delete-space',
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
            return url_for('space_view', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'new-proposal':
            return url_for('proposal_new', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'json':
            return url_for('space_view_json', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'csv':
            return url_for('space_view_csv', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'edit':
            return url_for('space_edit', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'transition':
            return url_for('space_transition', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'sections':
            return url_for('section_list', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'new-section':
            return url_for('section_new', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'usergroups':
            return url_for('usergroup_list', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'new-usergroup':
            return url_for('usergroup_new', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'venues':
            return url_for('venue_list', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'new-venue':
            return url_for('venue_new', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'schedule':
            return url_for('schedule_view', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'edit-schedule':
            return url_for('schedule_edit', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'update-schedule':
            return url_for('schedule_update', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'new-session':
            return url_for('session_new', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'update-venue-colors':
            return url_for('update_venue_colors', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'json-schedule':
            return url_for('schedule_json', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'subscribe-schedule':
            return url_for('schedule_subscribe', profile=self.profile.name, space=self.name, _external=_external)
        elif action == 'ical-schedule':
            return url_for('schedule_ical', profile=self.profile.name, space=self.name, _external=_external).replace('https:', 'webcals:').replace('http:', 'webcal:')
        elif action == 'rsvp':
            return url_for('rsvp', profile=self.profile.name, space=self.name)
        elif action == 'rsvp-list':
            return url_for('rsvp_list', profile=self.profile.name, space=self.name)
        elif action == 'admin':
            return url_for('admin', profile=self.profile.name, space=self.name)
        elif action == 'events':
            return url_for('events', profile=self.profile.name, space=self.name)
        elif action == 'participants':
            return url_for('participants', profile=self.profile.name, space=self.name)
        elif action == 'new-participant':
            return url_for('new_participant', profile=self.profile.name, space=self.name)
        elif action == 'new-ticket-type-participant':
            return url_for('new_ticket_type_participant', profile=self.profile.name, space=self.name)
        elif action == 'new-event':
            return url_for('new_event', profile=self.profile.name, space=self.name)
        elif action == 'new-ticket-type':
            return url_for('new_ticket_type', profile=self.profile.name, space=self.name)
        elif action == 'new-ticket-client':
            return url_for('new_ticket_client', profile=self.profile.name, space=self.name)

    @classmethod
    def all(cls):
        """
        Return currently active events, sorted by date.
        """
        return cls.query.filter(cls.state.CURRENTLY_LISTED).order_by(cls.date.desc()).all()

    @classmethod
    def fetch_sorted(cls):
        # sorts the spaces so that both new and old spaces are sorted from closest to farthest
        now = db.func.utcnow()
        currently_listed_spaces = cls.query.filter_by(parent_space=None).filter(
            cls.state.CURRENTLY_LISTED
            )
        upcoming = currently_listed_spaces.filter(cls.date >= now).order_by(cls.date.asc())
        past = currently_listed_spaces.filter(cls.date < now).order_by(cls.date.desc())

        # union_all() because union() doesn't respect the orders mentioned in subqueries
        return upcoming.union_all(past)

    def roles_for(self, actor=None, anchors=()):
        roles = super(ProposalSpace, self).roles_for(actor, anchors)
        if actor is not None:
            if self.admin_team in actor.teams:
                roles.add('admin')
            if self.review_team in actor.teams:
                roles.add('reviewer')
            roles.add('reader')  # https://github.com/hasgeek/funnel/pull/220#discussion_r168718052
        roles.update(self.profile.roles_for(actor, anchors))
        return roles


class ProposalSpaceRedirect(TimestampMixin, db.Model):
    __tablename__ = "proposal_space_redirect"

    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False, primary_key=True)
    profile = db.relationship(Profile, backref=db.backref('space_redirects', cascade='all, delete-orphan'))
    parent = db.synonym('profile')
    name = db.Column(db.Unicode(250), nullable=False, primary_key=True)

    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id', ondelete='SET NULL'), nullable=True)
    proposal_space = db.relationship(ProposalSpace, backref='redirects')

    def __repr__(self):
        return '<ProposalSpaceRedirect %s/%s: %s>' % (self.profile.name, self.name,
            self.proposal_space.name if self.proposal_space else "(none)")

    def redirect_view_args(self):
        if self.proposal_space:
            return {
                'profile': self.profile.name,
                'space': self.proposal_space.name
                }
        else:
            return {}

    @classmethod
    def migrate_profile(cls, oldprofile, newprofile):
        """
        There's no point trying to migrate redirects when merging profiles, so discard them.
        """
        oldprofile.space_redirects = []
        return [cls.__table__.name]
