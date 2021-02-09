from werkzeug.utils import cached_property

from coaster.sqlalchemy import immutable, with_roles

from . import User, db
from .commentvote import Commentset
from .helpers import reopen
from .membership import ImmutableMembershipMixin

__all__ = ['CommentsetMembership']


class CommentsetMembership(ImmutableMembershipMixin, db.Model):
    """Membership roles for users who are commentset users and subscribers."""

    __tablename__ = 'commentset_membership'

    __data_columns__ = ('last_seen_at',)

    __roles__ = {
        'subject': {
            'read': {
                'urls',
                'user',
                'commentset',
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

    parent = immutable(db.synonym('commentset'))
    parent_id = immutable(db.synonym('commentset_id'))

    #: when the user visited this commentset last
    last_seen_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )

    @cached_property
    def offered_roles(self):
        """
        Roles offered by this membership record.

        It won't be used though because relationship below ignores it.
        """
        return {'document_subscriber'}


@reopen(User)
class User:  # type: ignore[no-redef]  # skipcq: PYL-E0102
    active_commentset_memberships = db.relationship(
        CommentsetMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            CommentsetMembership.user_id == User.id,
            CommentsetMembership.is_active,
        ),
        viewonly=True,
    )


@reopen(Commentset)
class Commentset:  # type: ignore[no-redef]  # skipcq: PYL-E0102
    active_memberships = with_roles(
        db.relationship(
            CommentsetMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                CommentsetMembership.commentset_id == Commentset.id,
                CommentsetMembership.is_active,
            ),
            viewonly=True,
        ),
        grants_via={'user': {'document_subscriber'}},
    )

    def update_last_seen_at(self, user: User):
        existing_ms = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if existing_ms is not None:
            existing_ms.last_seen_at = db.func.utcnow()

    def add_subscriber(self, actor: User, user: User) -> bool:
        """Return True is subscriber is added, False if already exists."""
        existing_ms = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if existing_ms is None:
            new_ms = CommentsetMembership(
                commentset=self,
                user=user,
                granted_by=actor,
            )
            db.session.add(new_ms)
            return True
        return False

    def remove_subscriber(self, actor: User, user: User) -> bool:
        """Return True is subscriber is removed, False if already removed."""
        existing_ms = CommentsetMembership.query.filter_by(
            commentset=self, user=user, is_active=True
        ).one_or_none()
        if existing_ms is not None:
            existing_ms.revoke(actor=actor)
            return True
        return False
