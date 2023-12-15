"""Site-level membership records."""

from __future__ import annotations

from werkzeug.utils import cached_property

from . import Mapped, Model, declared_attr, sa, sa_orm
from .membership_mixin import ImmutableUserMembershipMixin

__all__ = ['SiteMembership']


class SiteMembership(ImmutableUserMembershipMixin, Model):
    """Membership roles for users who are site administrators."""

    __tablename__ = 'site_membership'

    # List of is_role columns in this model
    __data_columns__ = {
        'is_comment_moderator',
        'is_user_moderator',
        'is_site_editor',
        'is_sysadmin',
    }

    __roles__ = {
        'member': {
            'read': {
                'urls',
                'member',
                'is_comment_moderator',
                'is_user_moderator',
                'is_site_editor',
                'is_sysadmin',
            }
        }
    }

    #: SiteMembership doesn't have a container limiting its scope
    parent_id = None
    parent_id_column = None
    parent = None

    # Site admin roles (at least one must be True):

    #: Comment moderators can delete comments
    is_comment_moderator: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    #: User moderators can suspend users
    is_user_moderator: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    #: Site editors can feature or reject projects
    is_site_editor: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    #: Sysadmins can manage technical settings
    is_sysadmin: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple:
        """Table arguments."""
        try:
            args = list(super().__table_args__)  # type: ignore[misc]
        except AttributeError:
            args = []
        args.append(
            sa.CheckConstraint(
                sa.or_(
                    cls.is_comment_moderator.is_(True),
                    cls.is_user_moderator.is_(True),
                    cls.is_site_editor.is_(True),
                    cls.is_sysadmin.is_(True),
                ),
                name='site_membership_has_role',
            )
        )
        return tuple(args)

    def __repr__(self) -> str:
        """Return representation of membership."""
        # pylint: disable=using-constant-test
        return (
            f'<{self.__class__.__name__} {self.member!r} '
            + ('active' if self.is_active else 'revoked')
            + '>'
        )

    @cached_property
    def offered_roles(self) -> set[str]:
        """
        Roles offered by this membership record.

        This property will typically not be used, as the ``Account.is_*`` properties
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
        if self.is_sysadmin:
            roles.add('sysadmin')
        return roles
