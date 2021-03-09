from sqlalchemy.exc import IntegrityError

from werkzeug.utils import invalidate_cached_property  # type: ignore[attr-defined]

import pytest

from funnel.models import SiteMembership


def invalidate_cache(user):
    """Remove cached properties."""
    for attr in (
        'is_site_admin',
        'is_comment_moderator',
        'is_user_moderator',
        'is_site_editor',
    ):
        invalidate_cached_property(user, attr)


def test_siteadmin_roles(db_session, new_user):
    """`SiteMembership` grants siteadmin roles."""
    assert new_user.active_site_membership is None
    assert new_user.is_site_admin is False
    assert new_user.is_comment_moderator is False
    assert new_user.is_user_moderator is False
    assert new_user.is_site_editor is False

    # Create membership granting all siteadmin roles
    membership = SiteMembership(
        user=new_user,
        is_comment_moderator=True,
        is_user_moderator=True,
        is_site_editor=True,
    )
    db_session.add(membership)
    db_session.commit()
    invalidate_cache(new_user)

    # Now confirm all roles are present
    assert new_user.active_site_membership == membership
    assert new_user.is_site_admin is True
    assert new_user.is_comment_moderator is True  # type: ignore[unreachable]
    assert new_user.is_user_moderator is True
    assert new_user.is_site_editor is True

    # Progressively revoke roles and confirm
    membership = membership.replace(actor=new_user, is_site_editor=False)
    db_session.commit()
    invalidate_cache(new_user)

    assert new_user.active_site_membership == membership
    assert new_user.is_site_admin is True
    assert new_user.is_comment_moderator is True
    assert new_user.is_user_moderator is True
    assert new_user.is_site_editor is False

    membership = membership.replace(actor=new_user, is_user_moderator=False)
    db_session.commit()
    invalidate_cache(new_user)

    assert new_user.active_site_membership == membership
    assert new_user.is_site_admin is True
    assert new_user.is_comment_moderator is True
    assert new_user.is_user_moderator is False
    assert new_user.is_site_editor is False

    # At least one role is required, so this will fail
    with pytest.raises(IntegrityError):
        membership.replace(actor=new_user, is_comment_moderator=False)
        db_session.commit()
    db_session.rollback()
    # The membership record must be revoked to remove all roles
    membership.revoke(actor=new_user)
    db_session.commit()
    invalidate_cache(new_user)

    assert new_user.active_site_membership is None
    assert new_user.is_site_admin is False
    assert new_user.is_comment_moderator is False
    assert new_user.is_user_moderator is False
    assert new_user.is_site_editor is False
