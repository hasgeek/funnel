"""Tests for Account (nee Profile) model."""

from sqlalchemy.exc import StatementError

from furl import furl
import pytest

from coaster.sqlalchemy import StateTransitionError
from funnel import models


def test_profile_urltype_valid(db_session, new_organization) -> None:
    profile = models.Profile.query.filter_by(id=new_organization.profile.id).first()
    assert profile.name == 'test-org'
    profile.logo_url = "https://images.example.com/"
    db_session.add(profile)
    db_session.commit()
    assert isinstance(profile.logo_url, furl)
    assert profile.logo_url.url == "https://images.example.com/"


def test_profile_urltype_invalid(db_session, new_organization) -> None:
    profile = models.Profile.query.filter_by(id=new_organization.profile.id).first()
    profile.logo_url = "noturl"
    db_session.add(profile)
    with pytest.raises(StatementError):
        db_session.commit()
    db_session.rollback()


def test_validate_name(new_organization) -> None:
    assert (
        models.Profile.validate_name_candidate(new_organization.profile.name) == 'org'
    )


def test_user_avatar(db_session, user_twoflower, user_rincewind) -> None:
    """User.avatar returns a coherent value despite content variations."""
    # Test fixture has what we need
    assert user_twoflower.profile is None
    assert user_rincewind.profile is not None
    assert user_rincewind.profile.logo_url is None
    db_session.commit()

    # Now test avatar is Optional[ImgeeFurl]
    assert user_twoflower.avatar is None
    assert user_rincewind.avatar is None

    user_rincewind.profile.logo_url = ''
    db_session.commit()
    assert str(user_rincewind.profile.logo_url) == ''
    assert user_rincewind.avatar is None

    user_rincewind.profile.logo_url = 'https://images.example.com/p.jpg'
    db_session.commit()
    assert str(user_rincewind.profile.logo_url) == 'https://images.example.com/p.jpg'
    assert user_rincewind.avatar == models.ImgeeFurl('https://images.example.com/p.jpg')


@pytest.mark.filterwarnings("ignore:Object of type <UserPhone> not in session")
def test_suspended_user_private_profile(db_session, user_wolfgang) -> None:
    """Suspending a user will mark their account page as private."""
    # Ensure column defaults are set (Profile.state)
    db_session.commit()

    # Account cannot be public until the user has a verified phone number
    with pytest.raises(StateTransitionError):
        user_wolfgang.profile.make_public()

    # Add a phone number to meet the criteria for having verified contact info
    user_wolfgang.add_phone('+12345678900')

    # Make account public and confirm
    user_wolfgang.profile.make_public()
    assert user_wolfgang.profile.state.PUBLIC

    # Suspend the user. Account can now be made private, but cannot be made public
    user_wolfgang.mark_suspended()
    # Commit to refresh profile.is_active column property
    db_session.commit()

    assert user_wolfgang.profile.state.PUBLIC
    user_wolfgang.profile.make_private()
    assert not user_wolfgang.profile.state.PUBLIC
    assert user_wolfgang.profile.state.PRIVATE

    # A suspended user's account cannot be made public
    with pytest.raises(StateTransitionError):
        user_wolfgang.profile.make_public()


def test_profile_autocomplete(
    user_rincewind, org_uu, user_lutze, user_librarian
) -> None:
    assert models.Profile.autocomplete('') == []
    assert models.Profile.autocomplete(' ') == []
    assert models.Profile.autocomplete('rin') == [user_rincewind.profile]
    assert models.Profile.autocomplete('u') == [org_uu.profile]
    assert models.Profile.autocomplete('unknown') == []
    assert models.Profile.autocomplete('l') == [
        user_librarian.profile,
        user_lutze.profile,
    ]