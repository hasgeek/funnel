from __future__ import annotations

from typing import Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import User, db
from .comment import Commentset
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin

__all__ = ['CommentsetMembership']


class CommentsetMembership(ImmutableUserMembershipMixin, db.Model):
    """Membership roles for users who are commentset users and subscribers."""

    __tablename__ = 'commentset_membership'

    __data_columns__ = ('last_seen_at', 'is_muted')

    __roles__ = {
        'subject': {
            'read': {
                'urls',
                'user',
                'commentset',
                'is_muted',
                'last_seen_at',
            }
        }
    }

    commentset_id = immutable(
        db.Column(
            None, db.ForeignKey('commentset.id', ondelete='CASCADE'), nullable=False
        )
    )
    commentset = immutable(
        db.relationship(
            'Commentset',
            backref=db.backref(
                'subscriber_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        )
    )

    parent = db.synonym('commentset')
    parent_id = db.synonym('commentset_id')

    #: Flag to indicate notifications are muted
    is_muted = db.Column(db.Boolean, nullable=False, default=False)
    #: When the user visited this commentset last
    last_seen_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )

    @cached_property
    def offered_roles(self) -> Set[str]:
        """
        Roles offered by this membership record.

        It won't be used though because relationship below ignores it.
        """
        return {'document_subscriber'}


@reopen(User)
class __User:
    active_commentset_memberships = db.relationship(
        CommentsetMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            CommentsetMembership.user_id == User.id,
            CommentsetMembership.is_active,
        ),
        viewonly=True,
    )

    subscribed_commentsets = DynamicAssociationProxy(
        'active_commentset_memberships', 'commentset'
    )


@reopen(Commentset)
class __Commentset:
    active_memberships = db.relationship(
        CommentsetMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            CommentsetMembership.commentset_id == Commentset.id,
            CommentsetMembership.is_active,
        ),
        viewonly=True,
    )

    # Send notifications only to subscribers who haven't muted
    active_memberships_unmuted = with_roles(
        db.relationship(
            CommentsetMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                CommentsetMembership.commentset_id == Commentset.id,
                CommentsetMembership.is_active,
                CommentsetMembership.is_muted.is_(False),
            ),
            viewonly=True,
        ),
        grants_via={'user': {'document_subscriber'}},
    )

    def update_last_seen_at(self, user: User) -> None:
        existing = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if existing is not None:
            existing.last_seen_at = db.func.utcnow()

    def add_subscriber(self, actor: User, user: User) -> bool:
        """Return True is subscriber is added, False if already exists."""
        existing = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if existing is None:
            db.session.add(
                CommentsetMembership(
                    commentset=self,
                    user=user,
                    granted_by=actor,
                )
            )
            return True
        return False

    def remove_subscriber(self, actor: User, user: User) -> bool:
        """Return True is subscriber is removed, False if already removed."""
        existing = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if existing is not None:
            existing.revoke(actor=actor)
            return True
        return False
