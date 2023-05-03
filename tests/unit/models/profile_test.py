"""Tests for Account (nee Profile) model."""

from sqlalchemy.exc import StatementError

from furl import furl
import pytest

from coaster.sqlalchemy import StateTransitionError
from funnel import models


def test_profile_urltype_valid(db_session, new_organization) -> None:
    profile = models.Profile.query.filter_by(id=new_organization.profile.id).first()
    assert profile.name == 'test_org'
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


@pytest.mark.filterwarnings("ignore:Object of type <AccountPhone> not in session")
def test_suspended_user_private_profile(db_session, user_wolfgang) -> None:
    """Suspending a user will mark their account page as private."""
    # Ensure column defaults are set (Profile.state)
    db_session.commit()

    # Account cannot be public until the user has a verified phone number
    with pytest.raises(StateTransitionError):
        user_wolfgang.make_profile_public()

    # Add a phone number to meet the criteria for having verified contact info
    user_wolfgang.add_phone('+12345678900')

    # Make account public and confirm
    user_wolfgang.make_profile_public()
    assert user_wolfgang.profile_state.PUBLIC

    # Suspend the user. Account can now be made private, but cannot be made public
    user_wolfgang.mark_suspended()
    # Commit to refresh profile.is_active column property
    db_session.commit()

    assert user_wolfgang.profile_state.PUBLIC
    user_wolfgang.make_profile_private()
    assert not user_wolfgang.profile_state.PUBLIC
    assert user_wolfgang.profile_state.PRIVATE

    # A suspended user's account cannot be made public
    with pytest.raises(StateTransitionError):
        user_wolfgang.make_profile_public()


def test_profile_name_is(user_rincewind, org_uu, user_lutze):
    """Test Profile.name_is to return a query filter."""
    assert (
        models.Profile.query.filter(models.Profile.name_is('rincewind')).one()
        == user_rincewind.profile
    )
    assert (
        models.Profile.query.filter(models.Profile.name_is('Rincewind')).one()
        == user_rincewind.profile
    )
    assert (
        models.Profile.query.filter(models.Profile.name_is('uu')).one()
        == org_uu.profile
    )
    assert (
        models.Profile.query.filter(models.Profile.name_is('UU')).one()
        == org_uu.profile
    )
    assert (
        models.Profile.query.filter(models.Profile.name_is('lu-tze')).one()
        == user_lutze.profile
    )
    assert (
        models.Profile.query.filter(models.Profile.name_is('lu_tze')).one()
        == user_lutze.profile
    )


def test_profile_name_in(user_rincewind, org_uu, user_lutze):
    """Test Profile.name_in to return a query filter."""
    assert models.Profile.query.filter(
        models.Profile.name_in(['lu-tze', 'lu_tze'])
    ).all() == [user_lutze.profile]
    assert set(
        models.Profile.query.filter(models.Profile.name_in(['rincewind', 'UU'])).all()
    ) == {user_rincewind.profile, org_uu.profile}


def test_profile_name_like(user_rincewind, user_ridcully, user_lutze):
    """Test Profile.name_like to return a query filter."""
    assert set(models.Profile.query.filter(models.Profile.name_like('r%')).all()) == {
        user_rincewind.profile,
        user_ridcully.profile,
    }
    assert models.Profile.query.filter(models.Profile.name_like('lu%')).all() == [
        user_lutze.profile
    ]
    assert models.Profile.query.filter(models.Profile.name_like(r'lu\_%')).all() == [
        user_lutze.profile
    ]
    assert models.Profile.query.filter(models.Profile.name_like('lu-%')).all() == [
        user_lutze.profile
    ]


def test_profile_autocomplete(
    user_rincewind, org_uu, user_lutze, user_librarian
) -> None:
    """Test Profile.autocomplete to return matching profiles given a prefix."""
    assert models.Profile.autocomplete('') == []
    assert models.Profile.autocomplete(' ') == []
    assert models.Profile.autocomplete('rin') == [user_rincewind.profile]
    assert models.Profile.autocomplete('u') == [org_uu.profile]
    assert models.Profile.autocomplete('unknown') == []
    assert models.Profile.autocomplete('l') == [
        user_librarian.profile,
        user_lutze.profile,
    ]
    assert models.Profile.autocomplete('lu_tze') == [user_lutze.profile]
    assert models.Profile.autocomplete('lu-tze') == [user_lutze.profile]
