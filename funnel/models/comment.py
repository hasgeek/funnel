"""Comment and Commentset models."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any

from werkzeug.utils import cached_property

from baseframe import _, __
from coaster.sqlalchemy import LazyRoleSet, RoleAccessProxy, StateManager, with_roles
from coaster.utils import LabeledEnum

from . import (
    BaseMixin,
    DynamicMapped,
    Mapped,
    Model,
    TSVectorType,
    UuidMixin,
    db,
    hybrid_property,
    relationship,
    sa,
    sa_orm,
)
from .account import (
    Account,
    DuckTypeAccount,
    deleted_account,
    removed_account,
    unknown_account,
)
from .helpers import MarkdownCompositeBasic, MessageComposite, add_search_trigger

__all__ = ['Comment', 'Commentset']


# --- Constants ------------------------------------------------------------------------


class COMMENTSET_STATE(LabeledEnum):  # noqa: N801
    DISABLED = (1, __("Disabled"))  # Disabled for all
    OPEN = (2, __("Open"))  # Open for all
    PARTICIPANTS = (3, __("Participants-only"))  # Only for participants
    COLLABORATORS = (4, __("Collaborators-only"))  # Only for editors/collaborators

    NOT_DISABLED = {OPEN, PARTICIPANTS, COLLABORATORS}


class COMMENT_STATE(LabeledEnum):  # noqa: N801
    # If you add any new state, you need to migrate the check constraint as well
    SUBMITTED = (1, 'submitted', __("Submitted"))
    SCREENED = (2, 'screened', __("Screened"))
    HIDDEN = (3, 'hidden', __("Hidden"))
    SPAM = (4, 'spam', __("Spam"))
    # Deleted state for when there are replies to be preserved
    DELETED = (5, 'deleted', __("Deleted"))
    VERIFIED = (6, 'verified', __("Verified"))

    PUBLIC = {SUBMITTED, VERIFIED}
    REMOVED = {SPAM, DELETED}
    REPORTABLE = {SUBMITTED, SCREENED, HIDDEN}
    VERIFIABLE = {SUBMITTED, SCREENED, HIDDEN, SPAM}


# What is this Commentset attached to?
# TODO: Deprecated, doesn't help as much as we thought it would
class SET_TYPE:  # noqa: N801
    PROJECT = 0
    PROPOSAL = 2
    COMMENT = 3
    UPDATE = 4


message_deleted = MessageComposite(__("[deleted]"), 'del')
message_removed = MessageComposite(__("[removed]"), 'del')


# --- Models ---------------------------------------------------------------------------


class Commentset(UuidMixin, BaseMixin[int, Account], Model):
    __tablename__ = 'commentset'
    #: Commentset state code
    _state: Mapped[int] = sa_orm.mapped_column(
        'state',
        sa.SmallInteger,
        StateManager.check_constraint('state', COMMENTSET_STATE, sa.SmallInteger),
        nullable=False,
        default=COMMENTSET_STATE.OPEN,
    )
    #: Commentset state manager
    state = StateManager['Commentset'](
        '_state', COMMENTSET_STATE, doc="Commentset state"
    )
    #: Type of parent object
    settype: Mapped[int | None] = with_roles(
        sa_orm.mapped_column('type', nullable=True),
        read={'all'},
        datasets={'primary'},
    )
    #: Count of comments, stored to avoid count(*) queries
    count: Mapped[int] = with_roles(
        sa_orm.mapped_column(default=0, nullable=False),
        read={'all'},
        datasets={'primary'},
    )
    #: Timestamp of last comment, for ordering.
    last_comment_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True),
        read={'all'},
        datasets={'primary'},
    )

    comments: DynamicMapped[Comment] = relationship(
        lazy='dynamic', back_populates='commentset'
    )
    toplevel_comments: DynamicMapped[Comment] = relationship(
        lazy='dynamic',
        primaryjoin=lambda: sa.and_(
            Comment.commentset_id == Commentset.id, Comment.in_reply_to_id.is_(None)
        ),
        viewonly=True,
    )
    active_memberships: DynamicMapped[CommentsetMembership] = relationship(
        lazy='dynamic',
        primaryjoin=lambda: sa.and_(
            CommentsetMembership.commentset_id == Commentset.id,
            CommentsetMembership.is_active,
        ),
        viewonly=True,
    )
    # Send notifications only to subscribers who haven't muted
    active_memberships_unmuted: DynamicMapped[CommentsetMembership] = with_roles(
        relationship(
            lazy='dynamic',
            primaryjoin=lambda: sa.and_(
                CommentsetMembership.commentset_id == Commentset.id,
                CommentsetMembership.is_active,
                CommentsetMembership.is_muted.is_(False),
            ),
            viewonly=True,
        ),
        grants_via={'member': {'document_subscriber'}},
    )

    project: Mapped[Project | None] = with_roles(
        relationship(uselist=False, back_populates='commentset'),
        grants_via={None: {'editor': 'document_subscriber'}},
    )
    proposal: Mapped[Proposal | None] = relationship(
        uselist=False, back_populates='commentset'
    )
    update: Mapped[Update | None] = relationship(
        uselist=False, back_populates='commentset'
    )

    __roles__ = {
        'all': {
            'read': {'project', 'proposal', 'update', 'urls'},
            'call': {'url_for', 'forms'},
        }
    }

    __datasets__ = {
        'primary': {'uuid_b58', 'url_name_uuid_b58', 'urls'},
        'related': {'uuid_b58', 'url_name_uuid_b58'},
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.count = 0

    @cached_property
    def parent(self) -> Project | Proposal | Update:
        # TODO: Move this to a CommentMixin that uses a registry, like EmailAddress
        if self.project is not None:
            return self.project
        if self.proposal is not None:
            return self.proposal
        if self.update is not None:
            return self.update
        raise TypeError("Commentset has an unknown parent")

    with_roles(parent, read={'all'}, datasets={'primary'})

    @cached_property
    def parent_type(self) -> str:
        return self.parent.__tablename__

    with_roles(parent_type, read={'all'})

    @cached_property
    def last_comment(self):
        return (
            self.comments.filter(Comment.state.PUBLIC)
            .order_by(Comment.created_at.desc())
            .first()
        )

    with_roles(last_comment, read={'all'}, datasets={'primary'})

    def roles_for(
        self, actor: Account | None = None, anchors: Sequence = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        parent_roles = self.parent.roles_for(actor, anchors)
        if 'participant' in parent_roles or 'commenter' in parent_roles:
            roles.add('parent_participant')
        return roles

    @with_roles(call={'all'})
    @state.requires(state.NOT_DISABLED)
    def post_comment(
        self, actor: Account, message: str, in_reply_to: Comment | None = None
    ) -> Comment:
        """Post a comment."""
        # TODO: Add role check for non-OPEN states. Either:
        # 1. Add checking for restrictions to the view (retaining @state.requires here),
        # 2. Make a CommentMixin (like EmailAddressMixin) and insert logic into the
        #    parent, which can override methods and add custom restrictions
        comment = Comment(
            posted_by=actor, commentset=self, message=message, in_reply_to=in_reply_to
        )
        self.count = Commentset.count + 1
        db.session.add(comment)
        return comment

    @state.transition(state.OPEN, state.DISABLED)
    def disable_comments(self):
        """Disable posting of comments."""

    @state.transition(state.DISABLED, state.OPEN)
    def enable_comments(self):
        """Enable posting of comments."""

    # Transitions for the other two states are pending on the TODO notes in post_comment

    def update_last_seen_at(self, member: Account) -> None:
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=member, is_active=True
        ).one_or_none()
        if subscription is not None:
            subscription.update_last_seen_at()

    def add_subscriber(self, actor: Account, member: Account) -> bool:
        """Return True is subscriber is added or unmuted, False if already exists."""
        changed = False
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=member, is_active=True
        ).one_or_none()
        if subscription is None:
            subscription = CommentsetMembership(
                commentset=self,
                member=member,
                granted_by=actor,
            )
            db.session.add(subscription)
            changed = True
        elif subscription.is_muted:
            subscription = subscription.replace(actor=actor, is_muted=False)
            changed = True
        subscription.update_last_seen_at()
        return changed

    def mute_subscriber(self, actor: Account, member: Account) -> bool:
        """Return True if subscriber was muted, False if already muted or missing."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=member, is_active=True
        ).one_or_none()
        if subscription is not None and not subscription.is_muted:
            subscription.replace(actor=actor, is_muted=True)
            return True
        return False

    def unmute_subscriber(self, actor: Account, member: Account) -> bool:
        """Return True if subscriber was unmuted, False if not muted or missing."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=member, is_active=True
        ).one_or_none()
        if subscription is not None and subscription.is_muted:
            subscription.replace(actor=actor, is_muted=False)
            return True
        return False

    def remove_subscriber(self, actor: Account, member: Account) -> bool:
        """Return True is subscriber is removed, False if already removed."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=member, is_active=True
        ).one_or_none()
        if subscription is not None:
            subscription.revoke(actor=actor)
            return True
        return False


class Comment(UuidMixin, BaseMixin[int, Account], Model):
    __tablename__ = 'comment'

    posted_by_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), default=None, nullable=True
    )
    _posted_by: Mapped[Account | None] = with_roles(
        relationship(back_populates='comments'),
        grants={'author'},
    )
    commentset_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('commentset.id'), default=None, nullable=False
    )
    commentset: Mapped[Commentset] = with_roles(
        relationship(back_populates='comments'),
        grants_via={None: {'document_subscriber'}},
    )

    in_reply_to_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('comment.id'), default=None, nullable=True
    )
    in_reply_to: Mapped[Comment] = relationship(
        back_populates='replies', remote_side='Comment.id'
    )
    replies: Mapped[list[Comment]] = relationship(back_populates='in_reply_to')

    _message, message_text, message_html = MarkdownCompositeBasic.create(
        'message', nullable=False
    )

    _state: Mapped[int] = sa_orm.mapped_column(
        'state',
        StateManager.check_constraint('state', COMMENT_STATE, sa.Integer),
        default=COMMENT_STATE.SUBMITTED,
        nullable=False,
    )
    state = StateManager['Comment'](
        '_state', COMMENT_STATE, doc="Current state of the comment"
    )

    edited_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True),
        read={'all'},
        datasets={'primary', 'related', 'json'},
    )

    #: Revision number maintained by SQLAlchemy, starting at 1
    revisionid: Mapped[int] = with_roles(sa_orm.mapped_column(), read={'all'})

    search_vector: Mapped[str] = sa_orm.mapped_column(
        TSVectorType(
            'message_text',
            weights={'message_text': 'A'},
            regconfig='english',
            hltext=lambda: Comment.message_html,
        ),
        nullable=False,
        deferred=True,
    )

    moderator_reports: DynamicMapped[CommentModeratorReport] = relationship(
        lazy='dynamic', back_populates='comment'
    )

    __table_args__ = (
        sa.Index('ix_comment_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __mapper_args__ = {'version_id_col': revisionid}

    __roles__ = {
        'all': {
            'read': {'created_at', 'urls', 'uuid_b58', 'has_replies', 'absolute_url'},
            'call': {'state', 'commentset', 'view_for', 'url_for'},
        },
        'replied_to_commenter': {'granted_via': {'in_reply_to': '_posted_by'}},
    }

    __datasets__ = {
        'primary': {'created_at', 'urls', 'uuid_b58', 'absolute_url'},
        'related': {'created_at', 'urls', 'uuid_b58', 'absolute_url'},
        'json': {'created_at', 'urls', 'uuid_b58', 'absolute_url'},
        'minimal': {'created_at', 'uuid_b58'},
    }
    __json_datasets__ = ('json',)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.commentset.last_comment_at = sa.func.utcnow()

    @cached_property
    def has_replies(self) -> bool:
        return bool(self.replies)

    @property
    def current_access_replies(self) -> list[RoleAccessProxy]:
        return [
            reply.current_access(datasets=('json', 'related'))
            for reply in self.replies
            if reply.state.PUBLIC
        ]

    with_roles(current_access_replies, read={'all'}, datasets={'related', 'json'})

    @hybrid_property
    def posted_by(self) -> Account | DuckTypeAccount:
        return (
            deleted_account
            if self.state.DELETED
            else removed_account
            if self.state.SPAM
            else unknown_account
            if self._posted_by is None
            else self._posted_by
        )

    @posted_by.inplace.setter  # type: ignore[arg-type]
    def _posted_by_setter(self, value: Account | None) -> None:
        self._posted_by = value

    @posted_by.inplace.expression  # type: ignore[arg-type]
    @classmethod
    def _posted_by_expression(cls) -> sa_orm.InstrumentedAttribute[Account | None]:
        """Return SQL Expression."""
        return cls._posted_by

    with_roles(
        posted_by, read={'all'}, datasets={'primary', 'related', 'json', 'minimal'}
    )

    @hybrid_property
    def message(self) -> MessageComposite | MarkdownCompositeBasic:
        """Return the message of the comment if not deleted or removed."""
        return (
            message_deleted
            if self.state.DELETED
            else message_removed
            if self.state.SPAM
            else self._message
        )

    @message.inplace.setter
    def _message_setter(self, value: Any) -> None:
        """Edit the message of a comment."""
        self._message = value

    @message.inplace.expression
    @classmethod
    def _message_expression(cls):
        """Return SQL expression for comment message column."""
        return cls._message

    with_roles(
        message, read={'all'}, datasets={'primary', 'related', 'json', 'minimal'}
    )

    @property
    def title(self) -> str:
        """A made-up title referring to the context for the comment."""
        obj = self.commentset.parent
        if obj is not None:
            return _("{user} commented on {obj}").format(
                user=self.posted_by.pickername, obj=obj.title
            )
        return _("{account} commented").format(  # type: ignore[unreachable]
            account=self.posted_by.pickername
        )

    with_roles(title, read={'all'}, datasets={'primary', 'related', 'json'})

    @property
    def badges(self) -> set[str]:
        badges = set()
        roles: set[str] | LazyRoleSet = set()
        if self.commentset.project is not None:
            roles = self.commentset.project.roles_for(self._posted_by)
        elif self.commentset.proposal is not None:
            roles = self.commentset.proposal.project.roles_for(self._posted_by)
            if 'submitter' in self.commentset.proposal.roles_for(self._posted_by):
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
            self.posted_by = None
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

    def was_reviewed_by(self, account: Account) -> bool:
        return CommentModeratorReport.query.filter(
            CommentModeratorReport.comment == self,
            CommentModeratorReport.resolved_at.is_(None),
            CommentModeratorReport.reported_by == account,
        ).notempty()

    def roles_for(
        self, actor: Account | None = None, anchors: Sequence = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        roles.add('reader')
        return roles


add_search_trigger(Comment, 'search_vector')


# Tail imports for type checking
from .commentset_membership import CommentsetMembership
from .moderation import CommentModeratorReport

if TYPE_CHECKING:
    from .project import Project
    from .proposal import Proposal
    from .update import Update
