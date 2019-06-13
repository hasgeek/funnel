# -*- coding: utf-8 -*-

from coaster.utils import LabeledEnum
from coaster.sqlalchemy import cached, StateManager
from baseframe import __

from . import db, BaseMixin, MarkdownColumn, UuidMixin, TSVectorType
from .user import User
from .helpers import add_search_trigger


__all__ = ['Voteset', 'Vote', 'Commentset', 'Comment']


# --- Constants ---------------------------------------------------------------

class COMMENT_STATE(LabeledEnum):
    # If you add any new state, you need to add a migration to modify the check constraint
    PUBLIC = (0, 'public', __("Public"))
    SCREENED = (1, 'screened', __("Screened"))
    HIDDEN = (2, 'hidden', __("Hidden"))
    SPAM = (3, 'spam', __("Spam"))
    DELETED = (4, 'deleted', __("Deleted"))  # For when there are children to be preserved


# What is this Voteset or Commentset attached to?
class SET_TYPE:
    PROJECT = 0
    PROPOSAL = 2
    COMMENT = 3


# --- Models ------------------------------------------------------------------

class Voteset(BaseMixin, db.Model):
    __tablename__ = 'voteset'
    type = db.Column(db.Integer, nullable=True)
    count = cached(db.Column(db.Integer, default=0, nullable=False))

    def __init__(self, **kwargs):
        super(Voteset, self).__init__(**kwargs)
        self.count = 0

    def vote(self, user, votedown=False):
        voteob = Vote.query.filter_by(user=user, voteset=self).first()
        if not voteob:
            voteob = Vote(user=user, voteset=self, votedown=votedown)
            self.count += 1 if not votedown else -1
            db.session.add(voteob)
        else:
            if voteob.votedown != votedown:
                self.count += 2 if not votedown else -2
            voteob.votedown = votedown
        return voteob

    def cancelvote(self, user):
        voteob = Vote.query.filter_by(user=user, voteset=self).first()
        if voteob:
            self.count += 1 if voteob.votedown else -1
            db.session.delete(voteob)

    def getvote(self, user):
        return Vote.query.filter_by(user=user, voteset=self).first()


class Vote(BaseMixin, db.Model):
    __tablename__ = 'vote'
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('votes', lazy='dynamic', cascade="all, delete-orphan"))
    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, primaryjoin=voteset_id == Voteset.id,
        backref=db.backref('votes', cascade="all, delete-orphan"))
    votedown = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "voteset_id"), {})


class Commentset(BaseMixin, db.Model):
    __tablename__ = 'commentset'
    type = db.Column(db.Integer, nullable=True)
    count = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, **kwargs):
        super(Commentset, self).__init__(**kwargs)
        self.count = 0


class Comment(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'comment'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('comments', lazy='dynamic', cascade="all, delete-orphan"))
    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(Commentset, primaryjoin=commentset_id == Commentset.id,
        backref=db.backref('comments', cascade="all, delete-orphan"))

    parent_id = db.Column(None, db.ForeignKey('comment.id'), nullable=True)
    children = db.relationship("Comment", backref=db.backref("parent", remote_side="Comment.id"))

    message = MarkdownColumn('message', nullable=False)

    _state = db.Column('state', db.Integer, StateManager.check_constraint('state', COMMENT_STATE),
        default=COMMENT_STATE.PUBLIC, nullable=False)
    state = StateManager('_state', COMMENT_STATE, doc="Current state of the comment.")

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    edited_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    search_vector = db.Column(TSVectorType('message_text', weights={'message_text': 'A'}), nullable=False)

    __table_args__ = (
        db.Index('ix_comment_search_vector', search_vector, postgresql_using='gin'),
        )

    def __init__(self, **kwargs):
        super(Comment, self).__init__(**kwargs)
        self.voteset = Voteset(type=SET_TYPE.COMMENT)

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
        return sorted(self.children, key=lambda child: child.voteset.count)

    def permissions(self, user, inherited=None):
        perms = super(Comment, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            perms.add('vote_comment')
            if user == self.user:
                perms.update([
                    'edit_comment',
                    'delete_comment'
                    ])
        return perms


add_search_trigger(Comment, 'search_vector')
