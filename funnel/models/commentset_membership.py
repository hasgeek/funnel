"""Model for membership to a commentset for new comment notifications."""

from __future__ import annotations

from typing import Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, with_roles

from . import DynamicMapped, Mapped, Model, Query, backref, db, relationship, sa
from .account import Account
from .comment import Comment, Commentset
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin
from .project import Project
from .proposal import Proposal
from .update import Update

__all__ = ['CommentsetMembership']


class CommentsetMembership(ImmutableUserMembershipMixin, Model):
    """Membership roles for users who are commentset users and subscribers."""

    __tablename__ = 'commentset_membership'
    __allow_unmapped__ = True

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

    commentset_id: Mapped[int] = sa.orm.mapped_column(
        sa.Integer,
        sa.ForeignKey('commentset.id', ondelete='CASCADE'),
        nullable=False,
    )
    commentset: Mapped[Commentset] = relationship(
        Commentset,
        backref=backref(
            'subscriber_memberships',
            lazy='dynamic',
            cascade='all',
            passive_deletes=True,
        ),
    )

    parent_id: Mapped[int] = sa.orm.synonym('commentset_id')
    parent_id_column = 'commentset_id'
    parent: Mapped[Commentset] = sa.orm.synonym('commentset')

    #: Flag to indicate notifications are muted
    is_muted = sa.orm.mapped_column(sa.Boolean, nullable=False, default=False)
    #: When the user visited this commentset last
    last_seen_at = sa.orm.mapped_column(
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
        """Mark the member as having seen this commentset just now."""
        self.last_seen_at = sa.func.utcnow()

    @classmethod
    def for_user(cls, user: Account) -> Query[CommentsetMembership]:
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


@reopen(Account)
class __Account:
    active_commentset_memberships: DynamicMapped[CommentsetMembership] = relationship(
        CommentsetMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            CommentsetMembership.member_id == Account.id,
            CommentsetMembership.is_active,
        ),
        viewonly=True,
    )

    subscribed_commentsets = DynamicAssociationProxy(
        'active_commentset_memberships', 'commentset'
    )


@reopen(Commentset)
class __Commentset:
    active_memberships: DynamicMapped[CommentsetMembership] = relationship(
        CommentsetMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            CommentsetMembership.commentset_id == Commentset.id,
            CommentsetMembership.is_active,
        ),
        viewonly=True,
    )

    # Send notifications only to subscribers who haven't muted
    active_memberships_unmuted: DynamicMapped[CommentsetMembership] = with_roles(
        relationship(
            CommentsetMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                CommentsetMembership.commentset_id == Commentset.id,
                CommentsetMembership.is_active,
                CommentsetMembership.is_muted.is_(False),
            ),
            viewonly=True,
        ),
        grants_via={'member': {'document_subscriber'}},
    )

    def update_last_seen_at(self, user: Account) -> None:
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=user, is_active=True
        ).one_or_none()
        if subscription is not None:
            subscription.update_last_seen_at()

    def add_subscriber(self, actor: Account, user: Account) -> bool:
        """Return True is subscriber is added or unmuted, False if already exists."""
        changed = False
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=user, is_active=True
        ).one_or_none()
        if subscription is None:
            subscription = CommentsetMembership(
                commentset=self,
                member=user,
                granted_by=actor,
            )
            db.session.add(subscription)
            changed = True
        elif subscription.is_muted:
            subscription = subscription.replace(actor=actor, is_muted=False)
            changed = True
        subscription.update_last_seen_at()
        return changed

    def mute_subscriber(self, actor: Account, user: Account) -> bool:
        """Return True if subscriber was muted, False if already muted or missing."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=user, is_active=True
        ).one_or_none()
        if not subscription.is_muted:
            subscription.replace(actor=actor, is_muted=True)
            return True
        return False

    def unmute_subscriber(self, actor: Account, user: Account) -> bool:
        """Return True if subscriber was unmuted, False if not muted or missing."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=user, is_active=True
        ).one_or_none()
        if subscription.is_muted:
            subscription.replace(actor=actor, is_muted=False)
            return True
        return False

    def remove_subscriber(self, actor: Account, user: Account) -> bool:
        """Return True is subscriber is removed, False if already removed."""
        subscription = CommentsetMembership.query.filter_by(
            commentset=self, member=user, is_active=True
        ).one_or_none()
        if subscription is not None:
            subscription.revoke(actor=actor)
            return True
        return False
