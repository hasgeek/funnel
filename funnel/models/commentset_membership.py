"""Model for membership to a commentset for new comment notifications."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

from werkzeug.utils import cached_property

from . import Mapped, Model, Query, relationship, sa, sa_orm
from .account import Account
from .membership_mixin import ImmutableUserMembershipMixin
from .project import Project
from .proposal import Proposal
from .update import Update

__all__ = ['CommentsetMembership']


class CommentsetMembership(ImmutableUserMembershipMixin, Model):
    """Membership roles for users who are commentset users and subscribers."""

    __tablename__ = 'commentset_membership'

    __data_columns__ = ('last_seen_at', 'is_muted')

    __roles__ = {
        'member': {
            'read': {
                'urls',
                'member',
                'commentset',
                'is_muted',
                'last_seen_at',
                'new_comment_count',
            }
        }
    }

    commentset_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer,
        sa.ForeignKey('commentset.id', ondelete='CASCADE'),
        nullable=False,
    )
    commentset: Mapped[Commentset] = relationship()

    parent_id: Mapped[int] = sa_orm.synonym('commentset_id')
    parent_id_column = 'commentset_id'
    parent: Mapped[Commentset] = sa_orm.synonym('commentset')

    #: Flag to indicate notifications are muted
    is_muted: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    #: When the user visited this commentset last
    last_seen_at: Mapped[datetime] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )

    if TYPE_CHECKING:
        # The implementation is at bottom, following the tail imports
        new_comment_count: Mapped[int]

    @cached_property
    def offered_roles(self) -> set[str]:
        """
        Roles offered by this membership record.

        It won't be used though because relationship below ignores it.
        """
        return {'document_subscriber'}

    def update_last_seen_at(self) -> None:
        """Mark the member as having seen this commentset just now."""
        self.last_seen_at = sa.func.utcnow()

    @classmethod
    def for_user(cls, account: Account) -> Query[Self]:
        """
        Return a query representing all active commentset memberships for a user.

        This classmethod mirrors the functionality in
        :attr:`Account.active_commentset_memberships` with the difference that since
        it's a query on the class, it returns an instance of the query subclass from
        Flask-SQLAlchemy and Coaster. Relationships use the main class from SQLAlchemy
        which is missing pagination and the empty/notempty methods.
        """
        return (
            cls.query.filter(
                cls.member == account,
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


# Tail imports
from .comment import Comment, Commentset

CommentsetMembership.new_comment_count = sa_orm.column_property(
    sa.select(sa.func.count(Comment.id))
    .where(Comment.commentset_id == CommentsetMembership.commentset_id)
    .where(Comment.state.PUBLIC)
    .where(Comment.created_at > CommentsetMembership.last_seen_at)
    .correlate_except(Comment)
    .scalar_subquery()
)
