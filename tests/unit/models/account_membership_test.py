"""Tests for AccountMembership models."""

import pytest

from funnel import models

from ...conftest import scoped_session


@pytest.fixture()
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
