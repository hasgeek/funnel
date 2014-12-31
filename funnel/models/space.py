# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseScopedNameMixin, MarkdownColumn
from .user import User, Team
from .profile import Profile
from .commentvote import VoteSpace, CommentSpace, SPACETYPE

__all__ = ['SPACESTATUS', 'ProposalSpace']


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

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    admin_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    admin_team = db.relationship(Team, foreign_keys=[admin_team_id])

    review_team_id = db.Column(None, db.ForeignKey('team.id'), nullable=True)
    review_team = db.relationship(Team, foreign_keys=[review_team_id])

    #: Redirect URLs from Funnel to Talkfunnel
    legacy_name = db.Column(db.Unicode(250), nullable=True, unique=True)

    __table_args__ = (db.UniqueConstraint('profile_id', 'name'),)

    def __init__(self, **kwargs):
        super(ProposalSpace, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSALSPACE)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSALSPACE)

    @property
    def rooms(self):
        return [room for venue in self.venues for room in venue.rooms]

    @property
    def proposals_by_status(self):
        from .proposal import Proposal, PROPOSALSTATUS
        return dict((status, Proposal.query.filter_by(proposal_space=self, status=status).order_by(db.desc('created_at')).all()) for (status, title) in PROPOSALSTATUS.items() if status != PROPOSALSTATUS.DRAFT)

    @property
    def proposals_by_confirmation(self):
        from .proposal import Proposal, PROPOSALSTATUS
        response = dict(
            confirmed=Proposal.query.filter_by(proposal_space=self, status=PROPOSALSTATUS.CONFIRMED).order_by(db.desc('created_at')).all(),
            unconfirmed=Proposal.query.filter(Proposal.proposal_space == self, Proposal.status != PROPOSALSTATUS.CONFIRMED, Proposal.status != PROPOSALSTATUS.DRAFT).order_by(db.desc('created_at')).all())
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
                    ])
            if self.review_team and user in self.review_team.users:
                perms.update([
                    'view-contactinfo',
                    'confirm-proposal',
                    'view-voteinfo',
                    'view-status',
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

    @classmethod
    def all(cls):
        """
        Return currently active events, sorted by date.
        """
        return cls.query.filter(cls.status >= 1).filter(cls.status <= 4).order_by(cls.date.desc()).all()
