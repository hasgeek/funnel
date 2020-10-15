from sqlalchemy.ext.hybrid import hybrid_property

from flask import current_app

from baseframe import _, __
from coaster.sqlalchemy import StateManager, cached, with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, MarkdownColumn, NoIdMixin, TSVectorType, UuidMixin, db
from .helpers import add_search_trigger, reopen
from .user import User, deleted_user, removed_user

__all__ = ['Comment', 'Commentset', 'Vote', 'Voteset']


# --- Constants ---------------------------------------------------------------


class COMMENT_STATE(LabeledEnum):  # NOQA: N801
    # If you add any new state, you need to add a migration to modify the check constraint
    SUBMITTED = (0, 'submitted', __("Submitted"))
    SCREENED = (1, 'screened', __("Screened"))
    HIDDEN = (2, 'hidden', __("Hidden"))
    SPAM = (3, 'spam', __("Spam"))
    # Deleted state for when there are replies to be preserved
    DELETED = (4, 'deleted', __("Deleted"))
    VERIFIED = (5, 'verified', __("Verified"))

    PUBLIC = {SUBMITTED, VERIFIED}
    REMOVED = {SPAM, DELETED}
    REPORTABLE = {SUBMITTED, SCREENED, HIDDEN}
    VERIFIABLE = {SUBMITTED, SCREENED, HIDDEN, SPAM}


# What is this Voteset or Commentset attached to?
# TODO: Deprecated, doesn't help as much as we thought it would
class SET_TYPE:  # NOQA: N801
    PROJECT = 0
    PROPOSAL = 2
    COMMENT = 3
    UPDATE = 4


# --- Models ------------------------------------------------------------------


class Voteset(BaseMixin, db.Model):
    __tablename__ = 'voteset'
    settype = db.Column('type', db.Integer, nullable=True)
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


class Vote(NoIdMixin, db.Model):
    __tablename__ = 'vote'
    voteset_id = db.Column(
        None, db.ForeignKey('voteset.id'), nullable=False, primary_key=True
    )
    voteset = db.relationship(
        Voteset,
        primaryjoin=voteset_id == Voteset.id,
        backref=db.backref('votes', cascade='all'),
    )
    user_id = db.Column(
        None, db.ForeignKey('user.id'), nullable=False, primary_key=True, index=True
    )
    user = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('votes', lazy='dynamic', cascade='all'),
    )
    votedown = db.Column(db.Boolean, default=False, nullable=False)

    @classmethod
    def migrate_user(cls, old_user, new_user):
        votesets = {vote.voteset for vote in new_user.votes}
        for vote in list(old_user.votes):
            if vote.voteset not in votesets:
                vote.user = new_user
            else:
                # Discard conflicting vote
                current_app.logger.warning(
                    "Discarding conflicting vote (down %r) from %r on voteset %d",
                    vote.votedown,
                    vote.user,
                    vote.voteset_id,
                )
                db.session.delete(vote)


class Commentset(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'commentset'
    settype = db.Column('type', db.Integer, nullable=True)
    count = db.Column(db.Integer, default=0, nullable=False)

    __roles__ = {
        'all': {
            'read': {'settype', 'count', 'project', 'proposal'},
            'call': {'url_for'},
        }
    }

    __datasets__ = {
        'primary': {'settype', 'count'},
        'related': {'uuid_b58', 'url_name_uuid_b58'},
    }

    def __init__(self, **kwargs):
        super(Commentset, self).__init__(**kwargs)
        self.count = 0

    @with_roles(read={'all'})
    @property
    def parent(self):
        # FIXME: Move this to a CommentMixin that uses a registry, like EmailAddress
        parent = None  # project or proposal object
        if self.project is not None:
            parent = self.project
        elif self.proposal is not None:
            parent = self.proposal
        return parent

    @with_roles(read={'all'})
    @property
    def parent_type(self):
        parent = self.parent
        if parent:
            return parent.__tablename__
        return None

    def permissions(self, user, inherited=None):
        perms = super().permissions(user, inherited)
        if user is not None:
            perms.add('new_comment')
            perms.add('vote_comment')
        return perms

    def roles_for(self, actor=None, anchors=()):
        roles = super().roles_for(actor, anchors)
        parent_roles = self.parent.roles_for(actor, anchors)
        if 'participant' in parent_roles or 'commenter' in parent_roles:
            roles.add('parent_participant')
        return roles


class Comment(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'comment'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    _user = db.relationship(
        User, backref=db.backref('comments', lazy='dynamic', cascade='all')
    )
    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = with_roles(
        db.relationship(Commentset, backref=db.backref('comments', cascade='all')),
        grants_via={None: {'document_subscriber'}},
    )

    in_reply_to_id = db.Column(None, db.ForeignKey('comment.id'), nullable=True)
    replies = db.relationship(
        'Comment', backref=db.backref('in_reply_to', remote_side='Comment.id')
    )

    _message = MarkdownColumn('message', nullable=False)

    _state = db.Column(
        'state',
        db.Integer,
        StateManager.check_constraint('state', COMMENT_STATE),
        default=COMMENT_STATE.SUBMITTED,
        nullable=False,
    )
    state = StateManager('_state', COMMENT_STATE, doc="Current state of the comment.")

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    edited_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True),
        read={'all'},
        datasets={'primary', 'related', 'json'},
    )

    __roles__ = {
        'all': {
            'read': {'created_at', 'urls', 'uuid_b58'},
            'call': {'state', 'commentset', 'view_for', 'url_for'},
        },
        'replied_to_commenter': {'granted_via': {'in_reply_to': '_user'}},
    }

    __datasets__ = {
        'primary': {'created_at', 'urls', 'uuid_b58'},
        'related': {'created_at', 'urls', 'uuid_b58'},
        'json': {'created_at', 'urls', 'uuid_b58'},
    }

    search_vector = db.deferred(
        db.Column(
            TSVectorType(
                'message_text',
                weights={'message_text': 'A'},
                regconfig='english',
                hltext=lambda: Comment.message_html,
            ),
            nullable=False,
        )
    )

    __table_args__ = (
        db.Index('ix_comment_search_vector', 'search_vector', postgresql_using='gin'),
    )

    def __init__(self, **kwargs):
        super(Comment, self).__init__(**kwargs)
        self.voteset = Voteset(settype=SET_TYPE.COMMENT)

    @with_roles(read={'all'}, datasets={'related', 'json'})
    @property
    def current_access_replies(self):
        return [
            reply.current_access(datasets=('json', 'related'))
            for reply in self.replies
            if reply.state.PUBLIC
        ]

    @hybrid_property
    def user(self):
        return (
            deleted_user
            if self.state.DELETED
            else removed_user
            if self.state.SPAM
            else self._user
        )

    @user.setter
    def user(self, value):
        self._user = value

    @user.expression
    def user(cls):  # NOQA: N805
        return cls._user

    with_roles(user, read={'all'}, datasets={'primary', 'related', 'json'})

    @hybrid_property
    def message(self):
        return (
            _('[deleted]')
            if self.state.DELETED
            else _('[removed]')
            if self.state.SPAM
            else self._message
        )

    @message.setter
    def message(self, value):
        self._message = value

    @message.expression
    def message(cls):  # NOQA: N805
        return cls._message

    with_roles(message, read={'all'}, datasets={'primary', 'related', 'json'})

    @with_roles(read={'all'}, datasets={'primary', 'related', 'json'})
    @property
    def absolute_url(self):
        return self.url_for()

    @with_roles(read={'all'}, datasets={'primary', 'related', 'json'})
    @property
    def title(self):
        obj = self.commentset.parent
        if obj:
            return _("{user} commented on {obj}").format(
                user=self.user.pickername, obj=obj.title
            )
        else:
            return _("{user} commented").format(user=self.user.pickername)

    @with_roles(read={'all'}, datasets={'related', 'json'})
    @property
    def badges(self):
        badges = set()
        if self.commentset.project is not None:
            if 'crew' in self.commentset.project.roles_for(self._user):
                badges.add(_("Crew"))
        elif self.commentset.proposal is not None:
            if self.commentset.proposal.user == self._user:
                badges.add(_("Proposer"))
            if 'crew' in self.commentset.proposal.project.roles_for(self._user):
                badges.add(_("Crew"))
        return badges

    @state.transition(None, state.DELETED)
    def delete(self):
        """
        Delete this comment.
        """
        if len(self.replies) > 0:
            self.user = None
            self.message = ''
        else:
            if self.in_reply_to and self.in_reply_to.state.DELETED:
                # If the comment this is replying to is deleted, ask it to reconsider
                # removing itself
                in_reply_to = self.in_reply_to
                in_reply_to.replies.remove(self)
                db.session.delete(self)
                in_reply_to.delete()
            else:
                db.session.delete(self)

    @state.transition(None, state.SPAM)
    def mark_spam(self):
        """
        Mark this comment as spam.
        """

    @state.transition(state.VERIFIABLE, state.VERIFIED)
    def mark_not_spam(self):
        """
        Mark this comment as not a spam.
        """

    def sorted_replies(self):
        return sorted(self.replies, key=lambda comment: comment.voteset.count)

    def permissions(self, user, inherited=None):
        perms = super(Comment, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            perms.add('vote_comment')
            if user == self._user:
                perms.add('edit_comment')
                perms.add('delete_comment')
        return perms

    def roles_for(self, actor=None, anchors=()):
        roles = super(Comment, self).roles_for(actor, anchors)
        roles.add('reader')
        if actor is not None:
            if actor == self._user:
                roles.add('author')
        return roles


add_search_trigger(Comment, 'search_vector')


@reopen(Commentset)
class Commentset:
    toplevel_comments = db.relationship(
        Comment,
        lazy='dynamic',
        primaryjoin=db.and_(
            Comment.commentset_id == Commentset.id, Comment.in_reply_to_id.is_(None)
        ),
        viewonly=True,
    )
