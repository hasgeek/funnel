from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable

from . import Commentset, User, db
from .helpers import reopen
from .membership import ImmutableMembershipMixin

__all__ = ['CommentsetMembership']


class CommentsetMembership(ImmutableMembershipMixin, db.Model):
    """Membership roles for users who are commentset users and subscribers."""

    __tablename__ = 'commentset_membership'

    # List of is_role columns in this model
    __data_columns__ = {'is_subscriber'}

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'user',
                'is_subscriber',
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
                'crew_memberships', lazy='dynamic', cascade='all', passive_deletes=True
            ),
        )
    )
    parent = immutable(db.synonym('commentset'))
    parent_id = immutable(db.synonym('commentset_id'))

    #: Subscribers are notified of all the new comments in a commentset
    is_subscriber = db.Column(db.Boolean, nullable=False, default=False)
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
        if self.is_subscriber:
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

    active_subscribed_commentset_memberships = db.relationship(
        CommentsetMembership,
        lazy='select',
        primaryjoin=db.and_(
            CommentsetMembership.user_id == User.id,
            CommentsetMembership.is_active,
            CommentsetMembership.is_subscriber.is_(True),
        ),
        viewonly=True,
    )

    commentsets = DynamicAssociationProxy('active_commentset_memberships', 'commentset')
    subscribed_commentsets = DynamicAssociationProxy(
        'active_subscribed_commentset_memberships', 'commentset'
    )
