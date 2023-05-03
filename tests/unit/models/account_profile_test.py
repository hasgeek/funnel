"""Tests for Account model's profile features."""

from sqlalchemy.exc import StatementError

from furl import furl
import pytest

from coaster.sqlalchemy import StateTransitionError
from funnel import models


def test_account_logo_url_valid(db_session, new_organization) -> None:
    assert new_organization.name == 'test_org'
    new_organization.logo_url = "https://images.example.com/"
    db_session.commit()  # Required to roundtrip logo_url from db and turn into furl
    assert isinstance(new_organization.logo_url, furl)
    assert new_organization.logo_url.url == "https://images.example.com/"


def test_account_logo_url_invalid(db_session, new_organization) -> None:
    new_organization.logo_url = "noturl"
    with pytest.raises(StatementError):
        db_session.commit()
    db_session.rollback()


def test_user_avatar(db_session, user_twoflower, user_rincewind) -> None:
    """User.logo_url returns a coherent value despite content variations."""
    # Test fixture has what we need
    assert user_twoflower.name is None
    assert user_rincewind.name is not None
    assert user_rincewind.logo_url is None
    db_session.commit()

    # Now test avatar is Optional[ImgeeFurl]
    assert user_twoflower.logo_url is None
    assert user_rincewind.logo_url is None

    user_rincewind.logo_url = ''
    db_session.commit()
    assert user_rincewind.logo_url is None

    user_rincewind.logo_url = 'https://images.example.com/p.jpg'
    db_session.commit()
    assert str(user_rincewind.logo_url) == 'https://images.example.com/p.jpg'
    assert user_rincewind.logo_url == models.ImgeeFurl(
        'https://images.example.com/p.jpg'
    )


@pytest.mark.filterwarnings("ignore:Object of type <AccountPhone> not in session")
def test_suspended_user_private_profile(db_session, user_wolfgang) -> None:
    """Suspending a user will mark their account page as private."""
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

    assert user_wolfgang.profile_state.PUBLIC
    user_wolfgang.make_profile_private()
    assert not user_wolfgang.profile_state.PUBLIC
    assert user_wolfgang.profile_state.PRIVATE

    # A suspended user's account cannot be made public
    with pytest.raises(StateTransitionError):
        user_wolfgang.make_profile_public()


def test_account_name_is(user_rincewind, org_uu, user_lutze):
    """Test Account.name_is to return a query filter."""
    assert (
        models.Account.query.filter(models.Account.name_is('rincewind')).one()
        == user_rincewind
    )
    assert (
        models.Account.query.filter(models.Account.name_is('Rincewind')).one()
        == user_rincewind
    )
    assert models.Account.query.filter(models.Account.name_is('uu')).one() == org_uu
    assert models.Account.query.filter(models.Account.name_is('UU')).one() == org_uu
    assert (
        models.Account.query.filter(models.Account.name_is('lu-tze')).one()
        == user_lutze
    )
    assert (
        models.Account.query.filter(models.Account.name_is('lu_tze')).one()
        == user_lutze
    )


def test_account_name_in(user_rincewind, org_uu, user_lutze):
    """Test Account.name_in to return a query filter."""
    assert models.Account.query.filter(
        models.Account.name_in(['lu-tze', 'lu_tze'])
    ).all() == [user_lutze]
    assert set(
        models.Account.query.filter(models.Account.name_in(['rincewind', 'UU'])).all()
    ) == {user_rincewind, org_uu}


def test_account_name_like(user_rincewind, user_ridcully, user_lutze):
    """Test Account.name_like to return a query filter."""
    assert set(models.Account.query.filter(models.Account.name_like('r%')).all()) == {
        user_rincewind,
        user_ridcully,
    }
    assert models.Account.query.filter(models.Account.name_like('lu%')).all() == [
        user_lutze
    ]
    assert models.Account.query.filter(models.Account.name_like(r'lu\_%')).all() == [
        user_lutze
    ]
    assert models.Account.query.filter(models.Account.name_like('lu-%')).all() == [
        user_lutze
    ]
