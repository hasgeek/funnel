from sqlalchemy.ext.hybrid import hybrid_property

from flask import current_app

from baseframe import _, __
from coaster.sqlalchemy import StateManager, cached
from coaster.utils import LabeledEnum

from . import BaseMixin, MarkdownColumn, NoIdMixin, TSVectorType, UuidMixin, db
from .helpers import add_search_trigger
from .user import User

__all__ = ['Comment', 'Commentset', 'Vote', 'Voteset']


# --- Constants ---------------------------------------------------------------


class COMMENT_STATE(LabeledEnum):  # NOQA: N801
    # If you add any new state, you need to add a migration to modify the check constraint
    PUBLIC = (0, 'public', __("Public"))
    SCREENED = (1, 'screened', __("Screened"))
    HIDDEN = (2, 'hidden', __("Hidden"))
    SPAM = (3, 'spam', __("Spam"))
    # Deleted state for when there are children to be preserved
    DELETED = (4, 'deleted', __("Deleted"))

    REMOVED = {SPAM, DELETED}


# What is this Voteset or Commentset attached to?
class SET_TYPE:  # NOQA: N801
    PROJECT = 0
    PROPOSAL = 2
    COMMENT = 3
    POST = 4


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

    def __init__(self, **kwargs):
        super(Commentset, self).__init__(**kwargs)
        self.count = 0

    @property
    def parent(self):
        parent = None  # project or proposal object
        if self.project is not None:
            parent = self.project
        elif self.proposal is not None:
            parent = self.proposal
        return parent

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


@Commentset.views('url')
def parent_comments_url(obj):
    url = None  # project or proposal object
    if obj.project is not None:
        url = obj.project.url_for('comments', _external=True)
    elif obj.proposal is not None:
        url = obj.proposal.url_for(_external=True)
    return url


class Comment(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'comment'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('comments', lazy='dynamic', cascade='all'),
    )
    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(
        Commentset,
        primaryjoin=commentset_id == Commentset.id,
        backref=db.backref('comments', cascade='all'),
    )

    parent_id = db.Column(None, db.ForeignKey('comment.id'), nullable=True)
    children = db.relationship(
        'Comment', backref=db.backref('parent', remote_side='Comment.id')
    )

    message = MarkdownColumn('message', nullable=False)

    _state = db.Column(
        'state',
        db.Integer,
        StateManager.check_constraint('state', COMMENT_STATE),
        default=COMMENT_STATE.PUBLIC,
        nullable=False,
    )
    state = StateManager('_state', COMMENT_STATE, doc="Current state of the comment.")

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    edited_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    __roles__ = {
        'all': {
            'read': {
                'absolute_url',
                'created_at',
                'edited_at',
                'user',
                'user_pickername',
                'title',
                'message',
                'message_body',
                'parent_id',
                'children_comments',
                'urls',
                'badges',
            },
            'call': {'state', 'commentset', 'view_for', 'url_for'},
        }
    }

    __datasets__ = {
        'primary': {
            'user',
            'message',
            'created_at',
            'edited_at',
            'absolute_url',
            'title',
        },
        'json': {
            'user_pickername',
            'message_body',
            'created_at',
            'edited_at',
            'absolute_url',
            'title',
            'message',
            'user',
            'children_comments',
            'urls',
            'badges',
        },
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

    @property
    def children_comments(self):
        return [child.current_access() for child in self.children if child.state.PUBLIC]

    @hybrid_property
    def user_pickername(self):
        return (
            '[deleted]'
            if self.state.DELETED
            else '[removed]'
            if self.state.SPAM
            else self.user.pickername
        )

    @hybrid_property
    def message_body(self):
        return (
            '[deleted]'
            if self.state.DELETED
            else '[removed]'
            if self.state.SPAM
            else self.message.text
        )

    @property
    def absolute_url(self):
        if self.commentset.proposal:
            return self.commentset.proposal.absolute_url + '#c' + self.uuid_b58
        elif self.commentset.project:
            return self.commentset.project.url_for('comments') + '#c' + self.uuid_b58

    @property
    def title(self):
        obj = self.commentset.proposal or self.commentset.project
        if obj:
            return _("{user} commented on {obj}").format(
                user=self.user_pickername, obj=obj.title
            )
        else:
            return _("{user} commented").format(user=self.user_pickername)

    @property
    def badges(self):
        badges = set()
        if self.commentset.project is not None:
            if 'crew' in self.commentset.project.roles_for(self.user):
                badges.add(_("Crew"))
        elif self.commentset.proposal is not None:
            if self.commentset.proposal.user == self.user:
                badges.add(_("Proposer"))
            if 'crew' in self.commentset.proposal.project.roles_for(self.user):
                badges.add(_("Crew"))
        return badges

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

    @state.transition(None, state.SPAM)
    def mark_spam(self):
        """
        Mark this comment as spam.
        """

    @state.transition(state.SPAM, state.PUBLIC)
    def mark_not_spam(self):
        """
        Mark this comment as not a spam.
        """

    def sorted_children(self):
        return sorted(self.children, key=lambda child: child.voteset.count)

    def permissions(self, user, inherited=None):
        perms = super(Comment, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            perms.add('vote_comment')
            if user == self.user:
                perms.add('edit_comment')
                perms.add('delete_comment')
        return perms

    def roles_for(self, actor=None, anchors=()):
        roles = super(Comment, self).roles_for(actor, anchors)
        roles.add('reader')
        if actor is not None:
            if actor == self.user:
                roles.add('author')
        return roles


add_search_trigger(Comment, 'search_vector')


@Comment.views('url')
def comment_url(obj):
    url = None
    commentset_url = obj.commentset.views.url()
    if commentset_url is not None:
        url = commentset_url + '#c' + obj.uuid_b58
    return url


@Commentset.views('json_comments')
def commentset_json(obj):
    return [
        comment.current_access(datasets=('json',))
        for comment in obj.parent_comments
        if comment.state.PUBLIC or comment.children is not None
    ]


Commentset.parent_comments = db.relationship(
    Comment,
    lazy='dynamic',
    primaryjoin=db.and_(
        Comment.commentset_id == Commentset.id, Comment.parent_id.is_(None),
    ),
    viewonly=True,
)
