import pytest

from funnel.models import OrganizationMembership, merge_users


@pytest.fixture()
def death_membership(db_session, org_ankhmorpork, user_death):
    membership = OrganizationMembership(organization=org_ankhmorpork, user=user_death)
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture()
def death_owner_membership(db_session, org_ankhmorpork, user_death):
    membership = OrganizationMembership(
        organization=org_ankhmorpork, user=user_death, is_owner=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture()
def rincewind_membership(db_session, org_ankhmorpork, user_rincewind):
    membership = OrganizationMembership(
        organization=org_ankhmorpork, user=user_rincewind
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture()
def rincewind_owner_membership(db_session, org_ankhmorpork, user_rincewind):
    membership = OrganizationMembership(
        organization=org_ankhmorpork, user=user_rincewind, is_owner=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


# --- Tests ----------------------------------------------------------------------------


def test_merge_without_membership(
    db_session, org_ankhmorpork, user_death, user_vetinari, user_rincewind
):
    """Merge without any memberships works."""
    assert org_ankhmorpork.active_admin_memberships.count() == 1
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari}
    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari}


def test_merge_with_death_membership(  # pylint: disable=too-many-arguments
    db_session,
    org_ankhmorpork,
    user_death,
    user_vetinari,
    user_rincewind,
    death_membership,
):
    """When only the older account has a membership, it works."""
    assert org_ankhmorpork.active_admin_memberships.count() == 2
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified
    assert death_membership.revoked_at is None


def test_merge_with_rincewind_membership(  # pylint: disable=too-many-arguments
    db_session,
    org_ankhmorpork,
    user_death,
    user_vetinari,
    user_rincewind,
    rincewind_membership,
):
    """When only the newer account has a membership, it is transferred."""
    assert org_ankhmorpork.active_admin_memberships.count() == 2
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_rincewind}
    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was transferred, not revoked
    assert rincewind_membership.revoked_at is None


def test_merge_with_admin_membership(  # pylint: disable=too-many-arguments
    db_session,
    org_ankhmorpork,
    user_death,
    user_vetinari,
    user_rincewind,
    death_membership,
    rincewind_membership,
):
    """When both have equal memberships, older account's is preserved."""
    assert org_ankhmorpork.active_admin_memberships.count() == 3
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified because .replace() found no changes
    assert death_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert rincewind_membership.revoked_at is not None


def test_merge_with_death_owner_membership(  # pylint: disable=too-many-arguments
    db_session,
    org_ankhmorpork,
    user_death,
    user_vetinari,
    user_rincewind,
    death_owner_membership,
    rincewind_membership,
):
    """When older user has more roles, older account's is preserved."""
    assert org_ankhmorpork.active_admin_memberships.count() == 3
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified because .replace() found no changes
    assert death_owner_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert rincewind_membership.revoked_at is not None


def test_merge_with_rincewind_owner_membership(  # pylint: disable=too-many-arguments
    db_session,
    org_ankhmorpork,
    user_death,
    user_vetinari,
    user_rincewind,
    death_membership,
    rincewind_owner_membership,
):
    """When newer user has more roles, both are revoked and new record is created."""
    assert org_ankhmorpork.active_admin_memberships.count() == 3
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_rincewind}
    assert set(org_ankhmorpork.admin_users) == {
        user_vetinari,
        user_death,
        user_rincewind,
    }
    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was replaced with an additional role
    assert death_membership.revoked_at is not None
    # Membership was revoked as part of the transfer
    assert rincewind_owner_membership.revoked_at is not None


def test_merge_with_owner_membership(  # pylint: disable=too-many-arguments
    db_session,
    org_ankhmorpork,
    user_death,
    user_vetinari,
    user_rincewind,
    death_owner_membership,
    rincewind_owner_membership,
):
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
    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death
    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_ankhmorpork.admin_users) == {user_vetinari, user_death}
    # Membership was not modified because .replace() found no changes
    assert death_owner_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert rincewind_owner_membership.revoked_at is not None


def test_merge_multiple_memberships(  # pylint: disable=too-many-arguments
    db_session,
    org_ankhmorpork,
    org_uu,
    user_death,
    user_rincewind,
    user_vetinari,
    user_ridcully,
    death_membership,
    rincewind_owner_membership,
):
    """Merger with memberships across organizations works."""
    uu_death_owner_membership = OrganizationMembership(
        organization=org_uu, user=user_death, is_owner=True
    )
    db_session.add(uu_death_owner_membership)
    db_session.commit()
    uu_rincewind_membership = OrganizationMembership(
        organization=org_uu, user=user_rincewind, is_owner=False
    )
    db_session.add(uu_rincewind_membership)
    db_session.commit()

    merged = merge_users(user_death, user_rincewind)
    db_session.commit()
    assert merged == user_death

    assert set(org_ankhmorpork.owner_users) == {user_vetinari, user_death}
    assert set(org_uu.owner_users) == {user_ridcully, user_death}
