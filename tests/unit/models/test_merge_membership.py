from datetime import timedelta
from types import SimpleNamespace

import pytest

from funnel.models import Organization, OrganizationMembership, User, db, merge_users


@pytest.fixture
def fixtures(db_session):
    owner = User(
        username='owner',
        fullname="Org Owner",
    )
    user1 = User(
        username='user1',
        fullname="User 1",
        created_at=db.func.utcnow() - timedelta(days=1),
    )
    user2 = User(
        username='user2',
        fullname="User 2",
    )
    org = Organization(
        name='test-org-membership-merge', title="Organization", owner=owner
    )
    db_session.add_all([owner, user1, user2, org])
    db_session.commit()

    return SimpleNamespace(**locals())


@pytest.fixture
def user1_membership(db_session, fixtures):
    membership = OrganizationMembership(organization=fixtures.org, user=fixtures.user1)
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture
def user1_owner_membership(db_session, fixtures):
    membership = OrganizationMembership(
        organization=fixtures.org, user=fixtures.user1, is_owner=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture
def user2_membership(db_session, fixtures):
    membership = OrganizationMembership(organization=fixtures.org, user=fixtures.user2)
    db_session.add(membership)
    db_session.commit()
    return membership


@pytest.fixture
def user2_owner_membership(db_session, fixtures):
    membership = OrganizationMembership(
        organization=fixtures.org, user=fixtures.user2, is_owner=True
    )
    db_session.add(membership)
    db_session.commit()
    return membership


# --- Tests ----------------------------------------------------------------------------


def test_merge_without_membership(db_session, fixtures):
    """Merge without any memberships works."""
    assert fixtures.org.active_admin_memberships.count() == 1
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {fixtures.owner}
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {fixtures.owner}


def test_merge_with_user1_membership(db_session, fixtures, user1_membership):
    """When only the older account has a membership, it works."""
    assert fixtures.org.active_admin_memberships.count() == 2
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user1}
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user1}
    # Membership was not modified
    assert user1_membership.revoked_at is None


def test_merge_with_user2_membership(db_session, fixtures, user2_membership):
    """When only the newer account has a membership, it is transferred."""
    assert fixtures.org.active_admin_memberships.count() == 2
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user2}
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user1}
    # Membership was transferred, not revoked
    assert user2_membership.revoked_at is None


def test_merge_with_admin_membership(
    db_session, fixtures, user1_membership, user2_membership
):
    """When both have equal memberships, older account's is preserved."""
    assert fixtures.org.active_admin_memberships.count() == 3
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {
        fixtures.owner,
        fixtures.user1,
        fixtures.user2,
    }
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert set(fixtures.org.owner_users) == {fixtures.owner}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user1}
    # Membership was not modified because .replace() found no changes
    assert user1_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert user2_membership.revoked_at is not None


def test_merge_with_user1_owner_membership(
    db_session, fixtures, user1_owner_membership, user2_membership
):
    """When older user has more roles, older account's is preserved."""
    assert fixtures.org.active_admin_memberships.count() == 3
    assert set(fixtures.org.owner_users) == {fixtures.owner, fixtures.user1}
    assert set(fixtures.org.admin_users) == {
        fixtures.owner,
        fixtures.user1,
        fixtures.user2,
    }
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert set(fixtures.org.owner_users) == {fixtures.owner, fixtures.user1}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user1}
    # Membership was not modified because .replace() found no changes
    assert user1_owner_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert user2_membership.revoked_at is not None


def test_merge_with_user2_owner_membership(
    db_session, fixtures, user1_membership, user2_owner_membership
):
    """When newer user has more roles, both are revoked and new record is created."""
    assert fixtures.org.active_admin_memberships.count() == 3
    assert set(fixtures.org.owner_users) == {fixtures.owner, fixtures.user2}
    assert set(fixtures.org.admin_users) == {
        fixtures.owner,
        fixtures.user1,
        fixtures.user2,
    }
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert set(fixtures.org.owner_users) == {fixtures.owner, fixtures.user1}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user1}
    # Membership was replaced with an additional role
    assert user1_membership.revoked_at is not None
    # Membership was revoked as part of the transfer
    assert user2_owner_membership.revoked_at is not None


def test_merge_with_owner_membership(
    db_session, fixtures, user1_owner_membership, user2_owner_membership
):
    """When both have equal superior memberships, older account's is preserved."""
    assert fixtures.org.active_admin_memberships.count() == 3
    assert set(fixtures.org.owner_users) == {
        fixtures.owner,
        fixtures.user1,
        fixtures.user2,
    }
    assert set(fixtures.org.admin_users) == {
        fixtures.owner,
        fixtures.user1,
        fixtures.user2,
    }
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert set(fixtures.org.owner_users) == {fixtures.owner, fixtures.user1}
    assert set(fixtures.org.admin_users) == {fixtures.owner, fixtures.user1}
    # Membership was not modified because .replace() found no changes
    assert user1_owner_membership.revoked_at is None
    # Membership was revoked as part of the transfer
    assert user2_owner_membership.revoked_at is not None
