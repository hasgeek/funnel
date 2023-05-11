"""Tests for Account (nee Profile) name."""

from sqlalchemy.exc import IntegrityError

import pytest

from funnel import models


def test_is_available_name(db_session, user_rincewind) -> None:
    """Names are only available if valid and unused."""
    db_session.commit()  # Required for profile.state to be set
    assert models.Profile.is_available_name('invalid-name') is False
    # Rincewind has an account (nee profile) in default 'auto' status (not public, not
    # private even)
    assert user_rincewind.profile.state.AUTO
    # even though account is not public, username is still unavailable
    assert models.Profile.is_available_name('rincewind') is False
    # any other random usernames are available
    assert models.Profile.is_available_name('wizzard') is True


@pytest.mark.usefixtures('user_rincewind', 'org_uu')
def test_validate_name_candidate(db_session) -> None:
    """The name validator returns error codes as expected."""
    assert (
        models.Profile.validate_name_candidate(None)  # type: ignore[arg-type]
        == 'blank'
    )
    assert models.Profile.validate_name_candidate('') == 'blank'
    assert models.Profile.validate_name_candidate('invalid-name') == 'invalid'
    assert models.Profile.validate_name_candidate('0123456789' * 7) == 'long'
    assert models.Profile.validate_name_candidate('0123456789' * 6) is None
    assert models.Profile.validate_name_candidate('ValidName') is None
    assert models.Profile.validate_name_candidate('test_reserved') is None
    db_session.add(models.Profile(name='test_reserved', reserved=True))
    db_session.commit()
    assert models.Profile.validate_name_candidate('test_reserved') == 'reserved'
    assert models.Profile.validate_name_candidate('Test_Reserved') == 'reserved'
    assert models.Profile.validate_name_candidate('TestReserved') is None
    assert models.Profile.validate_name_candidate('rincewind') == 'user'
    assert models.Profile.validate_name_candidate('uu') == 'org'
    assert models.Profile.validate_name_candidate('UU') == 'org'


def test_reserved_name(db_session) -> None:
    """Names can be reserved, with no user or organization."""
    reserved_name = models.Profile(name='reserved_name', reserved=True)
    db_session.add(reserved_name)
    db_session.commit()
    # Use a model query since Profile.get() only works for public accounts
    retrieved_name = models.Profile.query.filter(
        models.Profile.name_is('reserved_name')
    ).first()
    assert retrieved_name is reserved_name
    assert reserved_name.user is None
    assert reserved_name.user_id is None
    assert reserved_name.organization is None
    assert reserved_name.organization_id is None

    reserved_name.name = 'Reserved_Name'
    db_session.commit()
    retrieved_name = models.Profile.query.filter(
        models.Profile.name_is('Reserved_Name')
    ).first()
    assert retrieved_name is reserved_name


def test_unassigned_name(db_session) -> None:
    """Names must be assigned to a user or organization if not reserved."""
    unassigned_name = models.Profile(name='unassigned')
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


def test_user_two_names(db_session, user_rincewind) -> None:
    """A user cannot have two names."""
    wizzard = models.Profile(name='wizzard', user=user_rincewind)
    db_session.add(wizzard)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_org_two_names(db_session, org_uu) -> None:
    """An organization cannot have two names."""
    assert org_uu.profile.name == 'UU'
    unseen = models.Profile(name='unseen', organization=org_uu)
    db_session.add(unseen)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_cant_remove_username(db_session, user_twoflower) -> None:
    """A user's username can be set or renamed but not removed."""
    db_session.commit()
    assert user_twoflower.username is None
    assert user_twoflower.profile is None

    user_twoflower.username = 'username'
    db_session.commit()
    assert user_twoflower.username == 'username'
    assert user_twoflower.profile is not None
    profile = user_twoflower.profile  # type: ignore[unreachable]
    assert isinstance(profile, models.Profile)

    user_twoflower.username = 'twoflower'
    db_session.commit()
    assert user_twoflower.username == 'twoflower'
    assert user_twoflower.profile is not None
    assert user_twoflower.profile == profile  # Renamed, not replaced

    # Can't be removed even though it was None to start with
    with pytest.raises(ValueError, match='Name is required'):
        user_twoflower.username = None

    # Can't be a blank value
    with pytest.raises(ValueError, match='Name is required'):
        user_twoflower.username = ''

    # Can't be an invalid value
    with pytest.raises(ValueError, match='Name is required'):
        user_twoflower.username = ' '


def test_cant_remove_orgname(db_session, org_uu) -> None:
    """An org's name can be renamed but not removed."""
    db_session.commit()
    assert org_uu.name == 'UU'
    assert org_uu.profile is not None
    profile = org_uu.profile

    org_uu.name = 'unseen'
    db_session.commit()

    assert org_uu.name == 'unseen'
    assert org_uu.profile == profile

    with pytest.raises(ValueError, match='Name is required'):
        org_uu.name = None


def test_name_transfer(db_session, user_mort, user_rincewind) -> None:
    """Merging user accounts will transfer the name."""
    db_session.commit()
    assert user_mort.username is None
    assert user_rincewind.username == 'rincewind'

    merged = models.merge_users(user_mort, user_rincewind)
    assert merged == user_mort
    assert user_mort.username == 'rincewind'
    assert user_rincewind.username is None
