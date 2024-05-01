"""Tests for AccountMembership models."""

# pylint: disable=redefined-outer-name

import pytest

from funnel import models

from ...conftest import scoped_session


@pytest.fixture
def placeholder_account(db_session: scoped_session) -> models.Placeholder:
    obj = models.Placeholder(name='placeholder', title='Placeholder')
    db_session.add(obj)
    return obj


@pytest.mark.parametrize(
    'account_fixture',
    [
        'user_vetinari',
        'user_rincewind',
        'user_twoflower',
        'org_ankhmorpork',
        'org_uu',
        'placeholder_account',
    ],
)
@pytest.mark.parametrize('role', ['follower', 'member', 'admin', 'owner'])
def test_user_account_has_roles_on_self(
    request: pytest.FixtureRequest, account_fixture: str, role: str
) -> None:
    """User accounts grant roles to self, but other account types don't."""
    account: models.Account = request.getfixturevalue(account_fixture)
    if account.is_user_profile:
        assert role in account.roles_for(account)
    else:
        assert role not in account.roles_for(account)


@pytest.fixture
def user_rincewind_follower(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_vetinari: models.User,
    user_rincewind: models.User,
) -> models.AccountMembership:
    m = models.AccountMembership(
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        member=user_rincewind,
        is_follower=True,
    )
    db_session.add(m)
    db_session.commit()
    return m


@pytest.fixture
def user_vimes_owner(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_vetinari: models.User,
    user_vimes: models.User,
) -> models.AccountMembership:
    m = models.AccountMembership(
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        member=user_vimes,
        is_owner=True,
    )
    db_session.add(m)
    db_session.commit()
    return m


@pytest.fixture
def user_ridcully_admin(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_vetinari: models.User,
    user_ridcully: models.User,
) -> models.AccountMembership:
    m = models.AccountMembership(
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        member=user_ridcully,
        is_admin=True,
    )
    db_session.add(m)
    db_session.commit()
    return m


def test_owner_is_admin(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_rincewind_follower: models.AccountMembership,
    user_vimes_owner: models.AccountMembership,
    user_ridcully_admin: models.AccountMembership,
) -> None:
    """An owner is an admin automatically, but not the other way."""
    assert user_rincewind_follower.is_follower is True
    assert user_rincewind_follower.is_admin is False
    assert user_rincewind_follower.is_owner is False

    assert user_vimes_owner.is_follower is False
    assert user_vimes_owner.is_admin is True
    assert user_vimes_owner.is_owner is True

    assert user_ridcully_admin.is_follower is False
    assert user_ridcully_admin.is_admin is True
    assert user_ridcully_admin.is_owner is False

    # Promote to owner and check admin flag
    user_rincewind_owner = user_rincewind_follower.replace(user_vetinari, is_owner=True)
    user_ridcully_owner = user_ridcully_admin.replace(user_vetinari, is_owner=True)
    db_session.commit()

    assert user_rincewind_owner is not user_rincewind_follower
    assert user_rincewind_owner.is_follower is True
    assert user_rincewind_owner.is_admin is True  # This was auto-set to True
    assert user_rincewind_owner.is_owner is True
    assert user_ridcully_owner is not user_ridcully_admin
    assert user_ridcully_owner.is_follower is False
    assert user_ridcully_owner.is_admin is True  # This remains true
    assert user_ridcully_owner.is_owner is True

    # Demote owner and check admin flag
    user_rincewind_demoted = user_rincewind_owner.replace(user_vetinari, is_owner=False)
    user_ridcully_demoted = user_ridcully_owner.replace(user_vetinari, is_owner=False)
    assert user_rincewind_demoted is not user_rincewind_owner
    assert user_rincewind_demoted is not user_rincewind_follower
    assert user_ridcully_demoted is not user_ridcully_owner
    assert user_ridcully_demoted is not user_ridcully_admin
    # Confirm owner flag removed, admin flag left as True, follower flag as original
    assert user_rincewind_demoted.is_owner is False
    assert user_ridcully_demoted.is_owner is False
    assert user_rincewind_demoted.is_admin is True
    assert user_ridcully_demoted.is_admin is True
    assert user_rincewind_demoted.is_follower is True
    assert user_ridcully_demoted.is_follower is False


def test_revoke_follower(
    user_rincewind_follower: models.AccountMembership,
    user_vimes_owner: models.AccountMembership,
) -> None:
    """Revoke a follower."""
    assert user_rincewind_follower.is_follower is True
    result = user_rincewind_follower.revoke_follower(user_rincewind_follower.member)
    assert result is None
    assert not user_rincewind_follower.is_active

    assert user_vimes_owner.is_follower is False
    result = user_vimes_owner.revoke_follower(user_vimes_owner.member)
    assert result is not None
    assert result is user_vimes_owner


def test_revoke_follower_who_is_also_admin(
    user_vetinari: models.User,
    user_rincewind_follower: models.AccountMembership,
) -> None:
    """A follower who becomes an admin can unfollow and remain an admin."""
    assert user_rincewind_follower.is_follower is True
    user_rincewind_admin = user_rincewind_follower.replace(user_vetinari, is_admin=True)
    assert user_rincewind_admin is not user_rincewind_follower
    assert not user_rincewind_follower.is_active
    assert user_rincewind_admin.is_follower is True
    assert user_rincewind_admin.is_admin is True
    user_rincewind_unfollowed = user_rincewind_admin.revoke_follower(
        user_rincewind_admin.member
    )
    assert user_rincewind_unfollowed is not None
    assert user_rincewind_unfollowed.is_follower is False
    assert user_rincewind_unfollowed.is_admin is True


def test_revoke_member(
    user_vetinari: models.User,
    user_rincewind_follower: models.AccountMembership,
    user_vimes_owner: models.AccountMembership,
    user_ridcully_admin: models.AccountMembership,
) -> None:
    """Revoke a member (admin/owner)."""
    # Make one admin also a follower for the test.
    user_ridcully_follower_admin = user_ridcully_admin.replace(
        user_ridcully_admin.member, is_follower=True
    )
    # Revoke admin/member status. This will revoke the membership unless they are also
    # a follower, in which case it will replace the membership with is_admin=False

    assert user_rincewind_follower.is_follower is True
    assert user_rincewind_follower.is_admin is False
    user_rincewind_revoked = user_rincewind_follower.revoke_member(user_vetinari)
    # No change since they're not an admin
    assert user_rincewind_revoked is user_rincewind_follower

    assert user_vimes_owner.is_follower is False
    assert user_vimes_owner.is_admin is True
    user_vimes_revoked = user_vimes_owner.revoke_member(user_vetinari)
    # Since they're not a follower, the membership is revoked
    assert user_vimes_revoked is None
    assert not user_vimes_owner.is_active

    assert user_ridcully_follower_admin.is_follower is True
    assert user_ridcully_follower_admin.is_admin is True
    user_ridcully_revoked = user_ridcully_follower_admin.revoke_member(user_vetinari)
    # Not an admin/owner anymore, but still a follower
    assert user_ridcully_revoked is not None
    assert user_ridcully_revoked is not user_ridcully_follower_admin
    assert user_ridcully_revoked is not user_ridcully_admin
    assert user_ridcully_revoked.is_follower is True
    assert user_ridcully_revoked.is_admin is False
