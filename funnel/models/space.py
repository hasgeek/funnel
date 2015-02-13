# -*- coding: utf-8 -*-

from flask import url_for
from . import db, TimestampMixin, BaseScopedNameMixin, MarkdownColumn
from .user import User, Team
from .profile import Profile
from .commentvote import VoteSpace, CommentSpace, SPACETYPE

__all__ = ['SPACESTATUS', 'ProposalSpace', 'ProposalSpaceRedirect']


# --- Constants ---------------------------------------------------------------

class SPACESTATUS:
    DRAFT = 0
    SUBMISSIONS = 1
    VOTING = 2
    JURY = 3
    FEEDBACK = 4
    CLOSED = 5
    WITHDRAWN = 6


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
    datelocation = db.Column(db.Unicode(50), default=u'', nullable=False)
    date = db.Column(db.Date, nullable=True)
    date_upto = db.Column(db.Date, nullable=True)
    website = db.Column(db.Unicode(250), nullable=True)
    timezone = db.Column(db.Unicode(40), nullable=False, default=u'UTC')
    status = db.Column(db.Integer, default=SPACESTATUS.DRAFT, nullable=False)

    # Columns for mobile
    bg_image = db.Column(db.Unicode(250), nullable=True)
    bg_color = db.Column(db.Unicode(6), nullable=True)
    explore_url = db.Column(db.Unicode(250), nullable=True)
    allow_rsvp = db.Column(db.Boolean, default=False, nullable=False)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    admin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    admin_team = db.relationship(Team, foreign_keys=[admin_team_id])

    review_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    review_team = db.relationship(Team, foreign_keys=[review_team_id])

    parent_space_id = db.Column(None, db.ForeignKey('proposal_space.id', ondelete='SET NULL'), nullable=True)
    parent_space = db.relationship('ProposalSpace', remote_side='ProposalSpace.id', backref='subspaces')

    #: Redirect URLs from Funnel to Talkfunnel
    legacy_name = db.Column(db.Unicode(250), nullable=True, unique=True)

    __table_args__ = (db.UniqueConstraint('profile_id', 'name'),)

    def __init__(self, **kwargs):
        super(ProposalSpace, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSALSPACE)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSALSPACE)

    def __repr__(self):
        return '<ProposalSpace %s/%s "%s">' % (self.profile.name if self.profile else "(none)", self.name, self.title)

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
    def proposals_by_status(self):
        from .proposal import Proposal, PROPOSALSTATUS
        if self.subspaces:
            basequery = Proposal.query.filter(Proposal.proposal_space_id.in_([self.id] + [s.id for s in self.subspaces]))
        else:
            basequery = Proposal.query.filter_by(proposal_space=self)
        return dict((status, basequery.filter_by(status=status).order_by(db.desc('created_at')).all()) for (status, title) in PROPOSALSTATUS.items() if status != PROPOSALSTATUS.DRAFT)

    @property
    def proposals_by_confirmation(self):
        from .proposal import Proposal, PROPOSALSTATUS
        if self.subspaces:
            basequery = Proposal.query.filter(Proposal.proposal_space_id.in_([self.id] + [s.id for s in self.subspaces]))
        else:
            basequery = Proposal.query.filter_by(proposal_space=self)
        response = dict(
            confirmed=basequery.filter_by(status=PROPOSALSTATUS.CONFIRMED).order_by(db.desc('created_at')).all(),
            unconfirmed=basequery.filter(Proposal.status != PROPOSALSTATUS.CONFIRMED, Proposal.status != PROPOSALSTATUS.DRAFT).order_by(db.desc('created_at')).all())
        return response

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
            if self.status == SPACESTATUS.SUBMISSIONS:
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

    @classmethod
    def all(cls):
        """
        Return currently active events, sorted by date.
        """
        return cls.query.filter(cls.status >= 1).filter(cls.status <= 4).order_by(cls.date.desc()).all()


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
