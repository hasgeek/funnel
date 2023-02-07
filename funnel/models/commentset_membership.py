"""Model for membership to a commentset for new comment notifications."""

from __future__ import annotations

from typing import Set
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, Query, with_roles

from . import Mapped, db, sa
from .comment import Comment, Commentset
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin
from .project import Project
from .proposal import Proposal
from .update import Update
from .user import User

__all__ = ['CommentsetMembership']


class CommentsetMembership(
    ImmutableUserMembershipMixin,
    db.Model,  # type: ignore[name-defined]
):
    """Membership roles for users who are commentset users and subscribers."""

    __tablename__ = 'commentset_membership'
    __allow_unmapped__ = True

    __data_columns__ = ('last_seen_at', 'is_muted')

    __roles__ = {
        'subject': {
            'read': {
                'urls',
                'user',
                'commentset',
                'is_muted',
                'last_seen_at',
                'new_comment_count',
            }
        }
    }

    commentset_id: Mapped[int] = sa.Column(
        sa.Integer,
        sa.ForeignKey('commentset.id', ondelete='CASCADE'),
        nullable=False,
    )
    commentset: Mapped[Commentset] = sa.orm.relationship(
        Commentset,
        backref=sa.orm.backref(
            'subscriber_memberships',
            lazy='dynamic',
            cascade='all',
            passive_deletes=True,
        ),
    )

    parent_id: int = sa.orm.synonym('commentset_id')
    parent_id_column = 'commentset_id'
    parent: Commentset = sa.orm.synonym('commentset')

    #: Flag to indicate notifications are muted
    is_muted = sa.Column(sa.Boolean, nullable=False, default=False)
    #: When the user visited this commentset last
    last_seen_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )

    new_comment_count: Mapped[int] = sa.orm.column_property(
        sa.select(sa.func.count(Comment.id))
        .where(Comment.commentset_id == commentset_id)  # type: ignore[has-type]
        .where(Comment.state.PUBLIC)  # type: ignore[has-type]
        .where(Comment.created_at > last_seen_at)
        .correlate_except(Comment)
        .scalar_subquery()
    )

    @cached_property
    def offered_roles(self) -> Set[str]:
        """
        Roles offered by this membership record.

        It won't be used though because relationship below ignores it.
        """
        return {'document_subscriber'}

    def update_last_seen_at(self) -> None:
        """Mark the subject user as having last seen this commentset just now."""
        self.last_seen_at = sa.func.utcnow()

    @classmethod
    def for_user(cls, user: User) -> Query:
        """
        Return a query representing all active commentset memberships for a user.

        This classmethod mirrors the functionality in
        :attr:`User.active_commentset_memberships` with the difference that since it's
        a query on the class, it returns an instance of the query subclass from
        Flask-SQLAlchemy and Coaster. Relationships use the main class from SQLAlchemy
        which is missing pagination and the empty/notempty methods.
        """
        return (
            cls.query.filter(
                cls.user == user,
                CommentsetMembership.is_active,
            )
            .join(Commentset)
            .outerjoin(Project, Project.commentset_id == Commentset.id)
            .outerjoin(Proposal, Proposal.commentset_id == Commentset.id)
            .outerjoin(Update, Update.commentset_id == Commentset.id)
            .order_by(
                Commentset.last_comment_at.is_(None),
                Commentset.last_comment_at.desc(),
                cls.granted_at.desc(),
            )
        )


@reopen(User)
class __User:
    active_commentset_memberships = sa.orm.relationship(
        CommentsetMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            CommentsetMembership.user_id == User.id,  # type: ignore[has-type]
            CommentsetMembership.is_active,  # type: ignore[arg-type]
        ),
        viewonly=True,
    )

    subscribed_commentsets = DynamicAssociationProxy(
        'active_commentset_memberships', 'commentset'
    )


@reopen(Commentset)
class __Commentset:
    active_memberships = sa.orm.relationship(
        CommentsetMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            CommentsetMembership.commentset_id == Commentset.id,
            CommentsetMembership.is_active,  # type: ignore[arg-type]
        ),
        viewonly=True,
    )

    # Send notifications only to subscribers who haven't muted
    active_memberships_unmuted = with_roles(
        sa.orm.relationship(
            CommentsetMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                CommentsetMembership.commentset_id == Commentset.id,
                CommentsetMembership.is_active,  # type: ignore[arg-type]
                CommentsetMembership.is_muted.is_(False),
            ),
            viewonly=True,
        ),
        grants_via={'user': {'document_subscriber'}},
    )

    def update_last_seen_at(self, user: User) -> None:
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if subscription is not None:
            subscription.update_last_seen_at()

    def add_subscriber(self, actor: User, user: User) -> bool:
        """Return True is subscriber is added or unmuted, False if already exists."""
        changed = False
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if subscription is None:
            subscription = CommentsetMembership(
                commentset=self,
                user=user,
                granted_by=actor,
            )
            db.session.add(subscription)
            changed = True
        elif subscription.is_muted:
            subscription = subscription.replace(actor=actor, is_muted=False)
            changed = True
        subscription.update_last_seen_at()
        return changed

    def mute_subscriber(self, actor: User, user: User) -> bool:
        """Return True if subscriber was muted, False if already muted or missing."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if not subscription.is_muted:
            subscription.replace(actor=actor, is_muted=True)
            return True
        return False

    def unmute_subscriber(self, actor: User, user: User) -> bool:
        """Return True if subscriber was unmuted, False if not muted or missing."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if subscription.is_muted:
            subscription.replace(actor=actor, is_muted=False)
            return True
        return False

    def remove_subscriber(self, actor: User, user: User) -> bool:
        """Return True is subscriber is removed, False if already removed."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if subscription is not None:
            subscription.revoke(actor=actor)
            return True
        return False
