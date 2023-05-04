"""Tests for Account name."""

from sqlalchemy.exc import IntegrityError

import pytest

from funnel import models


def test_is_available_name(db_session, user_rincewind) -> None:
    """Names are only available if valid and unused."""
    assert models.Account.is_available_name('invalid-name') is False
    # Rincewind has an account (nee profile) in default 'auto' status (not public, not
    # private even)
    assert user_rincewind.profile_state.AUTO
    # even though account is not public, username is still unavailable
    assert models.Account.is_available_name('rincewind') is False
    # any other random usernames are available
    assert models.Account.is_available_name('wizzard') is True


@pytest.mark.usefixtures('user_rincewind', 'org_uu')
def test_validate_name_candidate(db_session) -> None:
    """The name validator returns error codes as expected."""
    assert (
        models.Account.validate_name_candidate(None)  # type: ignore[arg-type]
        == 'blank'
    )
    assert models.Account.validate_name_candidate('') == 'blank'
    assert models.Account.validate_name_candidate('invalid-name') == 'invalid'
    assert models.Account.validate_name_candidate('0123456789' * 7) == 'long'
    assert models.Account.validate_name_candidate('0123456789' * 6) is None
    assert models.Account.validate_name_candidate('ValidName') is None
    assert models.Account.validate_name_candidate('test_reserved') is None
    db_session.add(models.Placeholder(name='test_reserved'))
    assert models.Account.validate_name_candidate('test_reserved') == 'reserved'
    assert models.Account.validate_name_candidate('Test_Reserved') == 'reserved'
    assert models.Account.validate_name_candidate('TestReserved') is None
    assert models.Account.validate_name_candidate('rincewind') == 'user'
    assert models.Account.validate_name_candidate('uu') == 'org'
    assert models.Account.validate_name_candidate('UU') == 'org'


def test_reserved_name(db_session) -> None:
    """Names can be reserved, with no user or organization."""
    reserved_name = models.Placeholder(name='reserved_name')
    db_session.add(reserved_name)
    retrieved_name = models.Account.query.filter(
        models.Account.name_is('reserved_name')
    ).first()
    assert retrieved_name is reserved_name
    assert isinstance(retrieved_name, models.Placeholder)

    reserved_name.name = 'Reserved_Name'
    retrieved_name = models.Account.query.filter(
        models.Account.name_is('Reserved_Name')
    ).first()
    assert retrieved_name is reserved_name


def test_unassigned_name(db_session) -> None:
    """Names must be assigned to a user or organization if not reserved."""
    unassigned_name = models.Account(name='unassigned')
    db_session.add(unassigned_name)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_double_assigned_name(db_session, user_rincewind) -> None:
    """Names cannot be assigned to a user and an organization simultaneously."""
    user = models.User(username="double_assigned", fullname="User")
    org = models.Organization(
        name="double_assigned", title="Organization", owner=user_rincewind
    )
    db_session.add_all([user, org])
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_cant_remove_username(db_session, user_twoflower) -> None:
    """A user's username can be set or renamed but not removed."""
    assert user_twoflower.username is None
    user_twoflower.username = 'username'
    assert user_twoflower.username == 'username'
    user_twoflower.username = 'twoflower'
    assert user_twoflower.username == 'twoflower'

    # Can't be removed even though it was None to start with
    with pytest.raises(ValueError, match='Account name cannot be unset'):
        user_twoflower.username = None

    # Can't be a blank value
    with pytest.raises(ValueError, match='Account name cannot be unset'):
        user_twoflower.username = ''

    # Can't be an invalid value
    with pytest.raises(ValueError, match='Invalid account name'):
        user_twoflower.username = ' '


def test_cant_remove_orgname(db_session, org_uu) -> None:
    """An org's name can be renamed but not removed."""
    assert org_uu.name == 'UU'
    org_uu.name = 'unseen'
    assert org_uu.name == 'unseen'
    with pytest.raises(ValueError, match='Account name cannot be unset'):
        org_uu.name = None


def test_name_transfer(db_session, user_mort, user_rincewind) -> None:
    """Merging user accounts will transfer the name."""
    assert user_mort.username is None
    assert user_rincewind.username == 'rincewind'
    db_session.commit()  # Commit because merge_accounts requires created_at set
    merged = models.merge_accounts(user_mort, user_rincewind)
    assert merged == user_mort
    assert user_mort.username == 'rincewind'
    assert user_rincewind.username is None
