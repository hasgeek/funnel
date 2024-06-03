"""Tests for following and unfollowing an account."""

import pytest
from werkzeug.datastructures import MultiDict

from funnel import models, redis_store

from ...conftest import LoginFixtureProtocol, TestClient, scoped_session


@pytest.mark.parametrize(
    'account_fixture',
    ['user_twoflower', 'user_rincewind', 'user_vetinari', 'org_ankhmorpork'],
)
def test_follow_account(
    request: pytest.FixtureRequest,
    db_session: scoped_session,
    client: TestClient,
    csrf_token: str,
    login: LoginFixtureProtocol,
    user_twoflower: models.User,
    account_fixture: str,
) -> None:
    """Follow a user account."""
    account: models.Account = request.getfixturevalue(account_fixture)
    account.make_profile_public()
    db_session.commit()
    assert account not in user_twoflower.accounts_following
    login.as_(user_twoflower)
    # Follow action succeeds and reports 201 except for self-follow
    rv = client.post(
        account.url_for('follow'),
        data=MultiDict({'csrf_token': csrf_token, 'follow': True}),
    )
    if account != user_twoflower:
        assert rv.status_code == 201
        assert account in user_twoflower.accounts_following
    else:
        assert rv.status_code == 422
    # A second follow action succeeds but reports 200 to indicate a no-op.
    # But first, clear idempotent_request decorator's cache
    redis_store.flushdb()
    rv = client.post(
        account.url_for('follow'),
        data=MultiDict({'csrf_token': csrf_token, 'follow': True}),
    )
    if account != user_twoflower:
        assert rv.status_code == 200
        assert account in user_twoflower.accounts_following
    else:
        assert rv.status_code == 422


@pytest.mark.parametrize(
    'account_fixture',
    ['user_twoflower', 'user_rincewind', 'user_vetinari', 'org_ankhmorpork'],
)
def test_unfollow_account(
    request: pytest.FixtureRequest,
    db_session: scoped_session,
    client: TestClient,
    csrf_token: str,
    login: LoginFixtureProtocol,
    user_twoflower: models.User,
    account_fixture: str,
) -> None:
    """Unfollow a user account."""
    account: models.Account = request.getfixturevalue(account_fixture)
    account.make_profile_public()
    db_session.commit()
    login.as_(user_twoflower)
    # First follow, disregarding the result
    client.post(
        account.url_for('follow'),
        data=MultiDict({'csrf_token': csrf_token, 'follow': True}),
    )
    if account != user_twoflower:
        assert account in user_twoflower.accounts_following
    # Then unfollow and confirm it happened
    rv = client.post(
        account.url_for('follow'),
        data=MultiDict({'csrf_token': csrf_token, 'follow': None}),
    )
    if account != user_twoflower:
        assert rv.status_code == 201
    else:
        assert rv.status_code == 422
    assert account not in user_twoflower.accounts_following
    # A second unfollow also succeeds, but returns 200 to indicate no-op.
    # But first, clear idempotent_request decorator's cache
    redis_store.flushdb()
    rv = client.post(
        account.url_for('follow'),
        data=MultiDict({'csrf_token': csrf_token, 'follow': None}),
    )
    if account != user_twoflower:
        assert rv.status_code == 200
    else:
        assert rv.status_code == 422
    assert account not in user_twoflower.accounts_following


def test_admin_follow_org(
    db_session: scoped_session,
    client: TestClient,
    csrf_token: str,
    login: LoginFixtureProtocol,
    org_ankhmorpork: models.Organization,
    user_vetinari: models.User,
) -> None:
    """As an account admin, follow the account."""
    org_ankhmorpork.make_profile_public()
    db_session.commit()
    assert user_vetinari in org_ankhmorpork.admin_users
    assert org_ankhmorpork in user_vetinari.accounts_following
    assert user_vetinari.accounts_following[org_ankhmorpork].is_follower is False
    login.as_(user_vetinari)
    # An account admin is an implicit follower, but this call makes it explicit
    rv = client.post(
        org_ankhmorpork.url_for('follow'),
        data=MultiDict({'csrf_token': csrf_token, 'follow': True}),
    )
    assert rv.status_code == 200
    assert org_ankhmorpork in user_vetinari.accounts_following
    assert user_vetinari.accounts_following[org_ankhmorpork].is_follower is True


def test_admin_unfollow_org(
    db_session: scoped_session,
    client: TestClient,
    csrf_token: str,
    login: LoginFixtureProtocol,
    org_ankhmorpork: models.Organization,
    user_vetinari: models.User,
) -> None:
    """As an account admin, unfollow the account."""
    org_ankhmorpork.make_profile_public()
    db_session.commit()
    assert user_vetinari in org_ankhmorpork.admin_users
    assert org_ankhmorpork in user_vetinari.accounts_following
    assert user_vetinari.accounts_following[org_ankhmorpork].is_follower is False
    login.as_(user_vetinari)
    # An account admin cannot unfollow the account
    rv = client.post(
        org_ankhmorpork.url_for('follow'),
        data=MultiDict({'csrf_token': csrf_token, 'follow': None}),
    )
    assert rv.status_code == 422
    # Admin remains an implicit follower (flag remains False)
    assert org_ankhmorpork in user_vetinari.accounts_following
    assert user_vetinari.accounts_following[org_ankhmorpork].is_follower is False
