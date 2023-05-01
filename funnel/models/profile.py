"""Account (nee Profile) model, linked to a User or Organization model."""

from __future__ import annotations

from typing import Iterable, List, Optional
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import

from coaster.sqlalchemy import LazyRoleSet

from . import BaseMixin, UuidMixin, db, sa
from .account import Account, Organization, User
from .helpers import quote_autocomplete_like
from .utils import do_migrate_instances

__all__ = ['Profile']


# This model does not use BaseNameMixin because it has no title column. The title comes
# from the linked User or Organization
class Profile(
    UuidMixin,
    BaseMixin,
    db.Model,  # type: ignore[name-defined]
):
    """
    Consolidated account for :class:`User` and :class:`Organization` models.

    Accounts (nee Profiles) hold the account name in a shared namespace between these
    models (aka "username"), and also host projects and other future document types.
    """

    __tablename__ = 'profile'
    __allow_unmapped__ = True
    __uuid_primary_key__ = False

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'uuid_b58',
                'name',
                'title',
                'description',
                'website',
                'logo_url',
                'user',
                'organization',
                'banner_image_url',
                'is_organization_profile',
                'is_user_profile',
                'owner',
            },
            'call': {'url_for', 'features', 'forms', 'state', 'views'},
        }
    }

    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'name',
            'title',
            'description',
            'logo_url',
            'website',
            'user',
            'organization',
            'owner',
            'is_verified',
        },
        'related': {
            'urls',
            'uuid_b58',
            'name',
            'title',
            'description',
            'logo_url',
            'is_verified',
        },
    }

    def roles_for(
        self, actor: Optional[User] = None, anchors: Iterable = ()
    ) -> LazyRoleSet:
        """Identify roles for the given actor."""
        if self.owner:
            roles = self.owner.roles_for(actor, anchors)
        else:
            roles = super().roles_for(actor, anchors)
        if self.state.PUBLIC:
            roles.add('reader')
        return roles

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        if old_account.profile is not None and new_account.profile is None:
            # New user doesn't have an account (nee profile). Simply transfer ownership
            new_account.profile = old_account.profile
        elif old_account.profile is not None and new_account.profile is not None:
            # Both have accounts. Move everything that refers to old account
            done = do_migrate_instances(
                old_account.profile, new_account.profile, 'migrate_profile'
            )
            if done:
                db.session.delete(old_account.profile)
        # Do nothing if old_user.profile is None and new_user.profile is not None

    def do_delete(self, actor: Account) -> bool:
        """Delete contents of this account."""
        if self.is_safe_to_delete():
            for membership in self.active_memberships():
                membership = membership.freeze_subject_attribution(actor)
                if membership.revoke_on_subject_delete:
                    membership.revoke(actor=actor)
            return True
        return False

    @classmethod
    def autocomplete(cls, prefix: str) -> List[Profile]:
        """
        Return accounts beginning with the prefix, for autocomplete UI.

        :param prefix: Letters to start matching with
        """
        like_query = quote_autocomplete_like(prefix)
        if not like_query or like_query == '@%':
            return []
        if prefix.startswith('@'):
            # Match only against `name` since ``@name...`` format is being used
            return (
                cls.query.options(sa.orm.defer(cls.is_active))
                .filter(cls.name_like(like_query[1:]))
                .order_by(cls.name)
                .all()
            )

        return (
            cls.query.options(sa.orm.defer(cls.is_active))
            .join(User)
            .filter(
                User.state.ACTIVE,
                sa.or_(
                    cls.name_like(like_query),
                    sa.func.lower(User.fullname).like(sa.func.lower(like_query)),
                ),
            )
            .union(
                cls.query.options(sa.orm.defer(cls.is_active))
                .join(Organization)
                .filter(
                    Organization.state.ACTIVE,
                    sa.or_(
                        cls.name_like(like_query),
                        sa.func.lower(Organization.title).like(
                            sa.func.lower(like_query)
                        ),
                    ),
                ),
            )
            .order_by(cls.name)
            .all()
        )
