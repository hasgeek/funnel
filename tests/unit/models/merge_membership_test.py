"""Tests for membership model mergers when merging user accounts."""

# pylint: disable=redefined-outer-name

import pytest

from funnel import models

from ...conftest import scoped_session


@pytest.fixture()
def death_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
) -> models.AccountMembership:
    membership = models.AccountMembership(
        account=org_ankhmorpork, member=user_death, is_admin=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture()
def death_owner_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
) -> models.AccountMembership:
    membership = models.AccountMembership(
        account=org_ankhmorpork, member=user_death, is_owner=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture()
def rincewind_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_rincewind: models.User,
) -> models.AccountMembership:
    membership = models.AccountMembership(
        account=org_ankhmorpork, member=user_rincewind, is_admin=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture()
def rincewind_owner_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_rincewind: models.User,
) -> models.AccountMembership:
    membership = models.AccountMembership(
        account=org_ankhmorpork, member=user_rincewind, is_owner=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


# MARK: Tests --------------------------------------------------------------------------


def test_merge_without_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
    user_vetinari: models.User,
    user_rincewind: models.User,
) -> None:
    """Merge without any memberships works."""
    assert org_ankhmorpork.active_admin_memberships.count() == 1
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari}
    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari}


def test_merge_with_death_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
    user_vetinari: models.User,
    user_rincewind: models.User,
    death_membership: models.AccountMembership,
) -> None:
    """When only the older account has a membership, it works."""
    assert org_ankhmorpork.active_admin_memberships.count() == 2
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified
    assert death_membership.revoked_at is None


def test_merge_with_rincewind_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
    user_vetinari: models.User,
    user_rincewind: models.User,
    rincewind_membership: models.AccountMembership,
) -> None:
    """When only the newer account has a membership, it is transferred."""
    assert org_ankhmorpork.active_admin_memberships.count() == 2
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_rincewind}
    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was transferred, not revoked
    assert rincewind_membership.revoked_at is None


def test_merge_with_admin_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
    user_vetinari: models.User,
    user_rincewind: models.User,
    death_membership: models.AccountMembership,
    rincewind_membership: models.AccountMembership,
) -> None:
    """When both have equal memberships, older account's is preserved."""
    assert org_ankhmorpork.active_admin_memberships.count() == 3
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified because .replace() found no changes
    assert death_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert rincewind_membership.revoked_at is not None


def test_merge_with_death_owner_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
    user_vetinari: models.User,
    user_rincewind: models.User,
    death_owner_membership: models.AccountMembership,
    rincewind_membership: models.AccountMembership,
) -> None:
    """When older user has more roles, older account's is preserved."""
    assert org_ankhmorpork.active_admin_memberships.count() == 3
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified because .replace() found no changes
    assert death_owner_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert rincewind_membership.revoked_at is not None


def test_merge_with_rincewind_owner_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
    user_vetinari: models.User,
    user_rincewind: models.User,
    death_membership: models.AccountMembership,
    rincewind_owner_membership: models.AccountMembership,
) -> None:
    """When newer user has more roles, both are revoked and new record is created."""
    assert org_ankhmorpork.active_admin_memberships.count() == 3
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_rincewind}
    assert set(org_ankhmorpork.admin_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was replaced with an additional role
    assert death_membership.revoked_at is not None
    # Membership was revoked as part of the transfer
    assert rincewind_owner_membership.revoked_at is not None


def test_merge_with_owner_membership(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_death: models.User,
    user_vetinari: models.User,
    user_rincewind: models.User,
    death_owner_membership: models.AccountMembership,
    rincewind_owner_membership: models.AccountMembership,
) -> None:
    """When both have equal superior memberships, older account's is preserved."""
    assert org_ankhmorpork.active_admin_memberships.count() == 3
    assert set(org_ankhmorpork.owner_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    assert set(org_ankhmorpork.admin_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified because .replace() found no changes
    assert death_owner_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert rincewind_owner_membership.revoked_at is not None


def test_merge_multiple_memberships(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    org_uu: models.Organization,
    user_death: models.User,
    user_rincewind: models.User,
    user_vetinari: models.User,
    user_ridcully: models.User,
    death_membership: models.AccountMembership,
    rincewind_owner_membership: models.AccountMembership,
) -> None:
    """Merger with memberships across organizations works."""
    uu_death_owner_membership = models.AccountMembership(
        account=org_uu, member=user_death, is_owner=True
    )
    db_session.add(uu_death_owner_membership)
    db_session.commit()
    uu_rincewind_membership = models.AccountMembership(
        account=org_uu, member=user_rincewind, is_admin=True
    )
    db_session.add(uu_rincewind_membership)
    db_session.commit()

    merged = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death

    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_uu.owner_users) == {user_ridcully, user_death}
