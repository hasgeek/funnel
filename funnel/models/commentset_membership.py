from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable

from . import Commentset, User, db
from .helpers import reopen
from .membership import ImmutableMembershipMixin

__all__ = ['CommentsetMembership']


class CommentsetMembership(ImmutableMembershipMixin, db.Model):
    """Membership roles for users who are commentset users and subscribers."""

    __tablename__ = 'commentset_membership'

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'user',
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
            Commentset,
            backref=db.backref(
                'subscriber_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        )
    )

    #: when the user visited this commentset last
    last_seen_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    @cached_property
    def offered_roles(self):
        """
        Roles offered by this membership record.

        This property will typically not be used, as the ``User.is_*`` properties
        directly test the role columns. This property exists solely to satisfy the
        :attr:`offered_roles` membership ducktype.
        """
        roles = {}
        if self.is_active:
            roles.add('commentset_subscriber')
        return roles


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

    # List of commentsets the user is subscribed to
    subscribed_commentsets = DynamicAssociationProxy(
        'active_commentset_memberships', 'commentset'
    )
