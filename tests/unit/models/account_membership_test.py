"""Tests for AccountMembership models."""

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


def test_owner_is_admin(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_vetinari: models.User,
    user_vimes: models.User,
    user_ridcully: models.User,
    user_rincewind: models.User,
) -> None:
    """An owner is always an admin automatically."""
    m1 = models.AccountMembership(
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        member=user_rincewind,
        is_follower=True,
    )
    db_session.add(m1)
    db_session.commit()
    assert m1.is_follower is True
    assert m1.is_admin is False
    assert m1.is_owner is False

    m2 = models.AccountMembership(
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        member=user_vimes,
        is_owner=True,
    )
    db_session.add(m2)
    db_session.commit()
    assert m2.is_follower is False
    assert m2.is_admin is True
    assert m2.is_owner is True

    m3 = models.AccountMembership(
        account=org_ankhmorpork,
        granted_by=user_ridcully,
        member=user_ridcully,
        is_follower=True,
    )
    db_session.add(m3)
    db_session.commit()
    assert m3.is_follower is True
    assert m3.is_admin is False
    assert m3.is_owner is False
    m3a = m3.replace(user_vetinari, is_owner=True)
    db_session.commit()
    assert m3a is not m3
    assert m3a.is_follower is True
    assert m3a.is_admin is True  # This was auto-set to True
    assert m3a.is_owner is True
