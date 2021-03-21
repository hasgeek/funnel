from sqlalchemy.ext.declarative import declared_attr

from werkzeug.utils import cached_property

from . import User, db
from .helpers import reopen
from .membership import ImmutableMembershipMixin

__all__ = ['SiteMembership']


class SiteMembership(ImmutableMembershipMixin, db.Model):
    """Membership roles for users who are site administrators."""

    __tablename__ = 'site_membership'

    # List of is_role columns in this model
    __data_columns__ = {'is_comment_moderator', 'is_user_moderator', 'is_site_editor'}

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'user',
                'is_comment_moderator',
                'is_user_moderator',
                'is_site_editor',
            }
        }
    }

    #: SiteMembership doesn't have a container limiting its scope
    parent_id = None

    # Site admin roles (at least one must be True):

    #: Comment moderators can delete comments
    is_comment_moderator = db.Column(db.Boolean, nullable=False, default=False)
    #: User moderators can suspend users
    is_user_moderator = db.Column(db.Boolean, nullable=False, default=False)
    #: Site editors can feature or reject projects
    is_site_editor = db.Column(db.Boolean, nullable=False, default=False)

    @declared_attr
    def __table_args__(cls):
        """Table arguments."""
        args = list(super().__table_args__)
        args.append(
            db.CheckConstraint(
                db.or_(
                    cls.is_comment_moderator.is_(True),
                    cls.is_user_moderator.is_(True),
                    cls.is_site_editor.is_(True),
                ),
                name='site_membership_has_role',
            )
        )
        return tuple(args)

    @cached_property
    def offered_roles(self):
        """
        Roles offered by this membership record.

        This property will typically not be used, as the ``User.is_*`` properties
        directly test the role columns. This property exists solely to satisfy the
        :attr:`offered_roles` membership ducktype.
        """
        roles = {'site_admin'}
        if self.is_comment_moderator:
            roles.add('comment_moderator')
        if self.is_user_moderator:
            roles.add('user_moderator')
        if self.is_site_editor:
            roles.add('site_editor')
        return roles


@reopen(User)
class User:  # type: ignore[no-redef]  # skipcq: PYL-E0102
    # Singular, as only one can be active
    active_site_membership = db.relationship(
        SiteMembership,
        lazy='select',
        primaryjoin=db.and_(
            SiteMembership.user_id == User.id,
            SiteMembership.is_active,
        ),
        viewonly=True,
        uselist=False,
    )

    @cached_property
    def is_comment_moderator(self) -> bool:
        return (
            self.active_site_membership is not None
            and self.active_site_membership.is_comment_moderator
        )

    @cached_property
    def is_user_moderator(self) -> bool:
        return (
            self.active_site_membership is not None
            and self.active_site_membership.is_user_moderator
        )

    @cached_property
    def is_site_editor(self) -> bool:
        return (
            self.active_site_membership is not None
            and self.active_site_membership.is_site_editor
        )

    # site_admin means user has one or more of above roles
    @cached_property
    def is_site_admin(self) -> bool:
        return self.active_site_membership is not None
