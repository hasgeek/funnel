# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseScopedNameMixin
from .space import ProposalSpace
from .commentvote import VoteSpace, CommentSpace, SPACETYPE

__all__ = ['ProposalSpaceSection']


# --- Models ------------------------------------------------------------------

class ProposalSpaceSection(BaseScopedNameMixin, db.Model):
    __tablename__ = 'proposal_space_section'
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref=db.backref('sections', cascade="all, delete-orphan"))
    parent = db.synonym('proposal_space')

    description = db.Column(db.Text, default=u'', nullable=False)
    public = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("proposal_space_id", "name"), {})

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    def __init__(self, **kwargs):
        super(ProposalSpaceSection, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSALSPACESECTION)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSALSPACESECTION)

    def permissions(self, user, inherited=None):
        perms = super(ProposalSpaceSection, self).permissions(user, inherited)
        if user is not None and user == self.proposal_space.user:
            perms.update([
                'edit-section',
                'delete-section',
                ])
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('section_view', space=self.proposal_space.name, section=self.name, _external=_external)
        elif action == 'edit':
            return url_for('section_edit', space=self.proposal_space.name, section=self.name, _external=_external)
        elif action == 'delete':
            return url_for('section_delete', space=self.proposal_space.name, section=self.name, _external=_external)
        elif action == 'usergroups':
            return url_for('usergroup_list', space=self.proposal_space.name, section=self.name, _external=_external)
