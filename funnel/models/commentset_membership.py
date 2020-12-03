from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy

from . import User, db
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

    #: Subscribers are notified of all the new comments in a commentset
    is_subscriber = db.Column(db.Boolean, nullable=False, default=False)

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
        lazy='select',
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
