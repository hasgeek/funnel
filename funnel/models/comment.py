from __future__ import annotations

from typing import Iterable, List, Optional, Set, Union

from flask import Markup

from baseframe import _, __
from coaster.sqlalchemy import RoleAccessProxy, StateManager, with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, MarkdownColumn, TSVectorType, UuidMixin, db, hybrid_property
from .helpers import add_search_trigger, reopen
from .user import DuckTypeUser, User, deleted_user, removed_user

__all__ = ['Comment', 'Commentset']


# --- Constants ------------------------------------------------------------------------


class COMMENT_STATE(LabeledEnum):  # NOQA: N801
    # If you add any new state, you need to migrate the check constraint as well
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


# What is this Commentset attached to?
# TODO: Deprecated, doesn't help as much as we thought it would
class SET_TYPE:  # NOQA: N801
    PROJECT = 0
    PROPOSAL = 2
    COMMENT = 3
    UPDATE = 4


# --- Models ---------------------------------------------------------------------------


class Commentset(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'commentset'
    #: Type of parent object
    settype = db.Column('type', db.Integer, nullable=True)
    #: Count of comments, stored to avoid count(*) queries
    count = db.Column(db.Integer, default=0, nullable=False)
    #: Timestamp of last comment, for ordering.
    last_comment_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.count = 0

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def parent(self) -> Optional[db.Model]:
        # FIXME: Move this to a CommentMixin that uses a registry, like EmailAddress
        parent = None  # project or proposal object
        if self.project is not None:
            parent = self.project
        elif self.proposal is not None:
            parent = self.proposal
        return parent

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def parent_type(self) -> Optional[str]:
        parent = self.parent
        if parent is not None:
            return parent.__tablename__
        return None

    def roles_for(self, actor: Optional[User], anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        parent_roles = self.parent.roles_for(actor, anchors)
        if 'participant' in parent_roles or 'commenter' in parent_roles:
            roles.add('parent_participant')
        return roles


class Comment(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'comment'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    _user = with_roles(
        db.relationship(
            User, backref=db.backref('comments', lazy='dynamic', cascade='all')
        ),
        grants={'author'},
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
    state = StateManager('_state', COMMENT_STATE, doc="Current state of the comment")

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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.commentset.last_comment_at = db.func.utcnow()

    @with_roles(read={'all'}, datasets={'related', 'json'})  # type: ignore[misc]
    @property
    def current_access_replies(self) -> List[RoleAccessProxy]:
        return [
            reply.current_access(datasets=('json', 'related'))
            for reply in self.replies
            if reply.state.PUBLIC
        ]

    @hybrid_property
    def user(self) -> Union[User, DuckTypeUser]:
        return (
            deleted_user
            if self.state.DELETED
            else removed_user
            if self.state.SPAM
            else self._user
        )

    @user.setter
    def user(self, value: Optional[User]) -> None:
        self._user = value

    @user.expression
    def user(cls):  # NOQA: N805
        return cls._user

    with_roles(user, read={'all'}, datasets={'primary', 'related', 'json'})

    @hybrid_property
    def message(self) -> Union[str, Markup]:
        return (
            _('[deleted]')
            if self.state.DELETED
            else _('[removed]')
            if self.state.SPAM
            else self._message
        )

    @message.setter
    def message(self, value: str) -> None:
        self._message = value

    @message.expression
    def message(cls):  # NOQA: N805
        return cls._message

    with_roles(message, read={'all'}, datasets={'primary', 'related', 'json'})

    @property
    def absolute_url(self) -> str:
        return self.url_for()

    with_roles(absolute_url, read={'all'}, datasets={'primary', 'related', 'json'})

    @property
    def title(self) -> str:
        obj = self.commentset.parent
        if obj is not None:
            return _("{user} commented on {obj}").format(
                user=self.user.pickername, obj=obj.title
            )
        return _("{user} commented").format(user=self.user.pickername)

    with_roles(title, read={'all'}, datasets={'primary', 'related', 'json'})

    @property
    def badges(self) -> Set[str]:
        badges = set()
        roles = set()
        if self.commentset.project is not None:
            roles = self.commentset.project.roles_for(self._user)
        elif self.commentset.proposal is not None:
            roles = self.commentset.proposal.project.roles_for(self._user)
            if 'submitter' in self.commentset.proposal.roles_for(self._user):
                badges.add(_("Submitter"))
        if 'editor' in roles:
            if 'promoter' in roles:
                badges.add(_("Editor & Promoter"))
            else:
                badges.add(_("Editor"))
        elif 'promoter' in roles:
            badges.add(_("Promoter"))
        return badges

    with_roles(badges, read={'all'}, datasets={'related', 'json'})

    @state.transition(None, state.DELETED)
    def delete(self) -> None:
        """Delete this comment."""
        if len(self.replies) > 0:
            self.user = None  # type: ignore[assignment]
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
    def mark_spam(self) -> None:
        """Mark this comment as spam."""

    @state.transition(state.VERIFIABLE, state.VERIFIED)
    def mark_not_spam(self) -> None:
        """Mark this comment as not spam."""

    def roles_for(self, actor: Optional[User], anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        roles.add('reader')
        return roles


add_search_trigger(Comment, 'search_vector')


@reopen(Commentset)
class __Commentset:
    toplevel_comments = db.relationship(
        Comment,
        lazy='dynamic',
        primaryjoin=db.and_(
            Comment.commentset_id == Commentset.id, Comment.in_reply_to_id.is_(None)
        ),
        viewonly=True,
    )
