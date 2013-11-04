# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseIdNameMixin, MarkdownColumn
from .user import User
from .space import ProposalSpace
from .section import ProposalSpaceSection
from .commentvote import CommentSpace, VoteSpace, SPACETYPE

__all__ = ['Proposal']


# --- Models ------------------------------------------------------------------

class Proposal(BaseIdNameMixin, db.Model):
    __tablename__ = 'proposal'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('proposals', cascade="all, delete-orphan"))

    speaker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    speaker = db.relationship(User, primaryjoin=speaker_id == User.id,
        backref=db.backref('speaker_at', cascade="all"))

    email = db.Column(db.Unicode(80), nullable=True)
    phone = db.Column(db.Unicode(80), nullable=True)
    bio = MarkdownColumn('bio', nullable=True)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref=db.backref('proposals', cascade="all, delete-orphan"))
    section_id = db.Column(db.Integer, db.ForeignKey('proposal_space_section.id'), nullable=True)
    section = db.relationship(ProposalSpaceSection, primaryjoin=section_id == ProposalSpaceSection.id,
        backref="proposals")
    objective = MarkdownColumn('objective', nullable=False)
    session_type = db.Column(db.Unicode(40), nullable=False, default=u'')
    technical_level = db.Column(db.Unicode(40), nullable=False)
    description = MarkdownColumn('description', nullable=False)
    requirements = MarkdownColumn('requirements', nullable=False)
    slides = db.Column(db.Unicode(250), default=u'', nullable=False)
    links = db.Column(db.Text, default=u'', nullable=False)
    status = db.Column(db.Integer, default=0, nullable=False)
    confirmed = db.Column(db.Boolean, default=False, nullable=False)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    edited_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super(Proposal, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSAL)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSAL)

    def __repr__(self):
        return u'<Proposal "%s" in space "%s" by "%s">' % (self.title, self.proposal_space.title, self.user.fullname)

    @property
    def owner(self):
        return self.speaker or self.user  

    @property
    def datetime(self):
        return self.created_at  # Until proposals have a workflow-driven datetime

    def getnext(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
                Proposal.created_at < self.created_at).order_by(db.desc('created_at')).first()

    def getprev(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
                Proposal.created_at > self.created_at).order_by('created_at').first()

    def permissions(self, user, inherited=None):
        perms = super(Proposal, self).permissions(user, inherited)
        if user is not None:
            perms.update([
                'vote-proposal',
                'new-comment',
                'vote-comment',
                ])
            if user == self.owner:
                perms.update([
                    'view-proposal',
                    'edit-proposal',
                    'delete-proposal',
                    'transfer-proposal',
                    ])
                if self.speaker != self.user:
                    perms.add('decline-proposal')  # Decline speaking
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('proposal_view', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'edit':
            return url_for('proposal_edit', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'confirm':
            return url_for('proposal_confirm', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'delete':
            return url_for('proposal_delete', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'voteup':
            return url_for('proposal_voteup', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'votedown':
            return url_for('proposal_votedown', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'cancelvote':
            return url_for('proposal_cancelvote', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'next':
            return url_for('proposal_next', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'prev':
            return url_for('proposal_prev', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
