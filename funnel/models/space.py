# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseNameMixin, MarkdownColumn
from .user import User
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

class ProposalSpace(BaseNameMixin, db.Model):
    __tablename__ = 'proposal_space'

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('spaces', cascade="all, delete-orphan"))
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = MarkdownColumn('description', default=u'', nullable=False)
    datelocation = db.Column(db.Unicode(50), default=u'', nullable=False)
    date = db.Column(db.Date, nullable=True)
    date_upto = db.Column(db.Date, nullable=True)
    website = db.Column(db.Unicode(250), nullable=True)
    timezone = db.Column(db.Unicode(40), nullable=False, default=u'UTC')
    status = db.Column(db.Integer, default=SPACESTATUS.DRAFT, nullable=False)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    def __init__(self, **kwargs):
        super(ProposalSpace, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSALSPACE)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSALSPACE)

    @property
    def rooms(self):
        return [room for venue in self.venues for room in venue.rooms]

    def permissions(self, user, inherited=None):
        perms = super(ProposalSpace, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            if self.status == SPACESTATUS.SUBMISSIONS:
                perms.add('new-proposal')
            if user == self.user:
                perms.update([
                    'edit-space',
                    'delete-space',
                    'view-section',
                    'new-section',
                    'view-usergroup',
                    'new-usergroup',
                    'confirm-proposal',
                    'new-venue',
                    'edit-venue',
                    'delete-venue',
                    ])
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('space_view', space=self.name, _external=_external)
        elif action == 'new-proposal':
            return url_for('proposal_new', space=self.name, _external=_external)
        elif action == 'json':
            return url_for('space_view_json', space=self.name, _external=_external)
        elif action == 'csv':
            return url_for('space_view_csv', space=self.name, _external=_external)
        elif action == 'edit':
            return url_for('space_edit', space=self.name, _external=_external)
        elif action == 'sections':
            return url_for('section_list', space=self.name, _external=_external)
        elif action == 'new-section':
            return url_for('section_new', space=self.name, _external=_external)
        elif action == 'usergroups':
            return url_for('usergroup_list', space=self.name, _external=_external)
        elif action == 'new-usergroup':
            return url_for('usergroup_new', space=self.name, _external=_external)
        elif action == 'venues':
            return url_for('venue_list', space=self.name, _external=_external)
        elif action == 'new-venue':
            return url_for('venue_new', space=self.name, _external=_external)
        elif action == 'schedule':
            return url_for('schedule_view', space=self.name, _external=_external)
        elif action == 'edit-schedule':
            return url_for('schedule_edit', space=self.name, _external=_external)
        elif action == 'update-schedule':
            return url_for('schedule_update', space=self.name, _external=_external)
        elif action == 'update-venue-colors':
            return url_for('update_venue_colors', space=self.name, _external=_external)
        elif action == 'json-schedule':
            return url_for('schedule_json', space=self.name, _external=_external)
