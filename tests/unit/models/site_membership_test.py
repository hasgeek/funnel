"""Tests for SiteMembership model."""

import pytest
from sqlalchemy.exc import IntegrityError

from funnel import models


def invalidate_cache(user):
    """Remove cached properties."""
    for attr in (
        'is_site_admin',
        'is_comment_moderator',
        'is_user_moderator',
        'is_site_editor',
    ):
        try:
            delattr(user, attr)
        except KeyError:
            # Not cached, ignore
            pass


def test_siteadmin_roles(db_session, user_mort, user_death) -> None:
    """`SiteMembership` grants siteadmin roles."""
    assert user_mort.active_site_membership is None
    assert user_mort.is_site_admin is False
    assert user_mort.is_comment_moderator is False
    assert user_mort.is_user_moderator is False
    assert user_mort.is_site_editor is False

    # Create membership granting all siteadmin roles
    membership = models.SiteMembership(
        member=user_mort,
        granted_by=user_death,
        is_comment_moderator=True,
        is_user_moderator=True,
        is_site_editor=True,
    )
    db_session.add(membership)
    db_session.commit()
    invalidate_cache(user_mort)

    # Now confirm all roles are present
    assert user_mort.active_site_membership == membership
    assert user_mort.is_site_admin is True
    assert user_mort.is_comment_moderator is True
    assert user_mort.is_user_moderator is True
    assert user_mort.is_site_editor is True

    # Progressively revoke roles and confirm
    membership = membership.replace(actor=user_mort, is_site_editor=False)
    db_session.commit()
    invalidate_cache(user_mort)

    assert user_mort.active_site_membership == membership
    assert user_mort.is_site_admin is True
    assert user_mort.is_comment_moderator is True
    assert user_mort.is_user_moderator is True
    assert user_mort.is_site_editor is False

    membership = membership.replace(actor=user_mort, is_user_moderator=False)
    db_session.commit()
    invalidate_cache(user_mort)

    assert user_mort.active_site_membership == membership
    assert user_mort.is_site_admin is True
    assert user_mort.is_comment_moderator is True
    assert user_mort.is_user_moderator is False
    assert user_mort.is_site_editor is False

    # At least one role is required, so this will fail
    membership.replace(actor=user_mort, is_comment_moderator=False)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    # The membership record must be revoked to remove all roles
    membership.revoke(actor=user_mort)
    db_session.commit()
    invalidate_cache(user_mort)

    assert user_mort.active_site_membership is None
    assert user_mort.is_site_admin is False
    assert user_mort.is_comment_moderator is False
    assert user_mort.is_user_moderator is False
    assert user_mort.is_site_editor is False


def test_site_membership_migrate_account_transfer(
    db_session, user_death, user_mort
) -> None:
    """Test for transfer of a site membership when merging users."""
    assert user_mort.active_site_membership is None
    assert user_death.active_site_membership is None

    # Create membership granting all siteadmin roles to Mort
    membership = models.SiteMembership(
        member=user_mort,
        granted_by=user_death,
        is_comment_moderator=True,
        is_user_moderator=True,
        is_site_editor=True,
    )
    db_session.add(membership)
    db_session.commit()
    invalidate_cache(user_mort)
    invalidate_cache(user_death)

    assert membership.member == user_mort
    assert user_mort.active_site_membership is not None
    assert user_death.active_site_membership is None

    models.SiteMembership.migrate_account(old_account=user_mort, new_account=user_death)
    db_session.commit()
    invalidate_cache(user_mort)
    invalidate_cache(user_death)

    # The membership record has been transferred
    assert membership.is_active
    assert membership.member == user_death
    assert user_mort.active_site_membership is None
    assert user_death.active_site_membership is not None


def test_site_membership_migrate_account_retain(
    db_session, user_death, user_mort
) -> None:
    """Test for retaining a site membership when merging users."""
    assert user_mort.active_site_membership is None
    assert user_death.active_site_membership is None

    # Create membership granting all siteadmin roles to Mort and then revoke it
    old_membership = models.SiteMembership(
        member=user_mort,
        granted_by=user_death,
        is_comment_moderator=True,
        is_user_moderator=True,
        is_site_editor=True,
    )
    db_session.add(old_membership)
    db_session.commit()
    old_membership.revoke(actor=user_mort)
    db_session.commit()

    # Create membership granting all siteadmin roles to Death
    membership = models.SiteMembership(
        member=user_death,
        granted_by=user_death,
        is_comment_moderator=True,
        is_user_moderator=True,
        is_site_editor=True,
    )
    db_session.add(membership)
    db_session.commit()
    invalidate_cache(user_mort)
    invalidate_cache(user_death)

    assert old_membership.member == user_mort
    assert membership.member == user_death
    assert user_mort.active_site_membership is None
    assert user_death.active_site_membership is not None

    models.SiteMembership.migrate_account(old_account=user_mort, new_account=user_death)
    db_session.commit()
    invalidate_cache(user_mort)
    invalidate_cache(user_death)

    # The old membership record for Mort record has been transferred to Death
    assert not old_membership.is_active
    assert old_membership.member == user_death
    # Death's membership record has been retained without amending
    assert membership.is_active
    assert membership.member == user_death
    assert user_mort.active_site_membership is None
    assert user_death.active_site_membership is not None


def test_site_membership_migrate_account_merge(
    db_session, user_death, user_mort
) -> None:
    """Test for merging site memberships when merging users."""
    assert user_mort.active_site_membership is None
    assert user_death.active_site_membership is None

    # Create membership granting one siteadmin role to Mort
    mort_membership = models.SiteMembership(
        member=user_mort,
        granted_by=user_death,
        is_comment_moderator=True,
        is_user_moderator=False,
        is_site_editor=False,
    )
    db_session.add(mort_membership)
    db_session.commit()

    # Create membership granting one siteadmin role to Death
    death_membership = models.SiteMembership(
        member=user_death,
        granted_by=user_death,
        is_comment_moderator=False,
        is_user_moderator=True,
        is_site_editor=False,
    )
    db_session.add(death_membership)
    db_session.commit()
    invalidate_cache(user_mort)
    invalidate_cache(user_death)

    assert mort_membership.member == user_mort
    assert death_membership.member == user_death
    assert user_mort.active_site_membership is not None
    assert user_death.active_site_membership is not None

    models.SiteMembership.migrate_account(old_account=user_mort, new_account=user_death)
    db_session.commit()
    invalidate_cache(user_mort)
    invalidate_cache(user_death)

    # The old membership record for Mort record has been revoked and transferred
    assert not mort_membership.is_active
    assert mort_membership.member == user_death
    # Death's membership record has been revoked as well
    assert not death_membership.is_active
    assert death_membership.member == user_death
    assert user_mort.active_site_membership is None
    assert user_death.active_site_membership is not None

    # Death's new membership record has acquired roles previously granted to Mort
    membership = user_death.active_site_membership
    assert membership.is_comment_moderator is True
    assert membership.is_user_moderator is True
    assert membership.is_site_editor is False  # This was not granted to either user


def test_amend_siteadmin(db_session, user_vetinari, user_vimes) -> None:
    """Amend a membership record."""
    membership = models.SiteMembership(
        member=user_vimes,
        granted_by=user_vetinari,
        is_comment_moderator=True,
        is_user_moderator=False,
        is_site_editor=False,
    )
    db_session.add(membership)
    db_session.commit()

    assert membership.revoked_at is None
    assert membership.is_active is True
    assert membership.is_comment_moderator is True
    assert membership.is_user_moderator is False
    assert membership.is_site_editor is False

    with membership.amend_by(user_vetinari) as amendment:
        assert amendment.membership is membership
        assert amendment.is_comment_moderator is True
        amendment.is_comment_moderator = False
        amendment.is_user_moderator = True

    assert amendment.membership is not membership
    assert membership.revoked_at is not None
    assert membership.is_active is False

    assert amendment.membership.revoked_at is None
    assert amendment.membership.is_active is True
    assert amendment.membership.is_comment_moderator is False
    assert amendment.membership.is_user_moderator is True
    assert amendment.membership.is_site_editor is False
