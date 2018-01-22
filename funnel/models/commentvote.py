# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseMixin, MarkdownColumn
from .user import User
from coaster.utils import LabeledEnum
from coaster.sqlalchemy import StateManager
from baseframe import __

__all__ = ['VoteSpace', 'Vote', 'CommentSpace', 'Comment']


# --- Constants ---------------------------------------------------------------

class COMMENTSTATUS(LabeledEnum):
    # If you add any new state, you need to add a migration to modify the check constraint
    PUBLIC = (0, 'public', __("Public"))
    SCREENED = (1, 'screened', __("Screened"))
    HIDDEN = (2, 'hidden', __("Hidden"))
    SPAM = (3, 'spam', __("Spam"))
    DELETED = (4, 'deleted', __("Deleted"))  # For when there are children to be preserved


# What is this VoteSpace or CommentSpace attached to?
class SPACETYPE:
    PROPOSALSPACE = 0
    PROPOSALSPACESECTION = 1
    PROPOSAL = 2
    COMMENT = 3


# --- Models ------------------------------------------------------------------

class VoteSpace(BaseMixin, db.Model):
    __tablename__ = 'votespace'
    type = db.Column(db.Integer, nullable=True)
    count = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, **kwargs):
        super(VoteSpace, self).__init__(**kwargs)
        self.count = 0

    def vote(self, user, votedown=False):
        voteob = Vote.query.filter_by(user=user, votespace=self).first()
        if not voteob:
            voteob = Vote(user=user, votespace=self, votedown=votedown)
            self.count += 1 if not votedown else -1
            db.session.add(voteob)
        else:
            if voteob.votedown != votedown:
                self.count += 2 if not votedown else -2
            voteob.votedown = votedown
        return voteob

    def cancelvote(self, user):
        voteob = Vote.query.filter_by(user=user, votespace=self).first()
        if voteob:
            self.count += 1 if voteob.votedown else -1
            db.session.delete(voteob)

    def getvote(self, user):
        return Vote.query.filter_by(user=user, votespace=self).first()


class Vote(BaseMixin, db.Model):
    __tablename__ = 'vote'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('votes', lazy='dynamic', cascade="all, delete-orphan"))
    votespace_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votespace = db.relationship(VoteSpace, primaryjoin=votespace_id == VoteSpace.id,
        backref=db.backref('votes', cascade="all, delete-orphan"))
    votedown = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "votespace_id"), {})


class CommentSpace(BaseMixin, db.Model):
    __tablename__ = 'commentspace'
    type = db.Column(db.Integer, nullable=True)
    count = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, **kwargs):
        super(CommentSpace, self).__init__(**kwargs)
        self.count = 0


class Comment(BaseMixin, db.Model):
    __tablename__ = 'comment'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('comments', lazy='dynamic', cascade="all, delete-orphan"))
    commentspace_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    commentspace = db.relationship(CommentSpace, primaryjoin=commentspace_id == CommentSpace.id,
        backref=db.backref('comments', cascade="all, delete-orphan"))

    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    children = db.relationship("Comment", backref=db.backref("parent", remote_side="Comment.id"))

    message = MarkdownColumn('message', nullable=False)

    _state = db.Column('status', db.Integer, StateManager.check_constraint('status', COMMENTSTATUS),
        default=COMMENTSTATUS.PUBLIC, nullable=False)
    state = StateManager('_state', COMMENTSTATUS, doc="Current state of the comment.")

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    edited_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super(Comment, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.COMMENT)

    @state.transition(None, state.DELETED)
    def delete(self):
        """
        Delete this comment.
        """
        if len(self.children) > 0:
            self.user = None
            self.message = ''
        else:
            if self.parent and self.parent.state.DELETED:
                # If the parent is deleted, ask it to reconsider removing itself
                parent = self.parent
                parent.children.remove(self)
                db.session.delete(self)
                parent.delete()
            else:
                db.session.delete(self)

    def sorted_children(self):
        return sorted(self.children, key=lambda child: child.votes.count)

    def permissions(self, user, inherited=None):
        perms = super(Comment, self).permissions(user, inherited)
        if user is not None and user == self.user:
            perms.update([
                'edit-comment',
                'delete-comment'
                ])
        return perms

    def url_for(self, action='view', proposal=None, _external=False):
        if action == 'view':
            return proposal.url_for(_external=_external) + "#c%d" % self.id
        elif action == 'json':
            return url_for('comment_json', profile=proposal.proposal_space.profile.name, space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)
        elif action == 'voteup':
            return url_for('comment_voteup', profile=proposal.proposal_space.profile.name, space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)
        elif action == 'votedown':
            return url_for('comment_votedown', profile=proposal.proposal_space.profile.name, space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)
        elif action == 'cancelvote':
            return url_for('comment_cancelvote', profile=proposal.proposal_space.profile.name, space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)
