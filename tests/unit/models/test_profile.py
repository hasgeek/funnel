from sqlalchemy.exc import StatementError

from furl import furl
import pytest

from coaster.sqlalchemy import StateTransitionError
from funnel.models import ImgeeFurl, Profile


def test_profile_urltype_valid(db_session, new_organization):
    profile = Profile.query.filter_by(id=new_organization.profile.id).first()
    assert profile.name == 'test-org'
    profile.logo_url = "https://images.example.com/"
    db_session.add(profile)
    db_session.commit()
    assert isinstance(profile.logo_url, furl)
    assert profile.logo_url.url == "https://images.example.com/"


def test_profile_urltype_invalid(db_session, new_organization):
    profile = Profile.query.filter_by(id=new_organization.profile.id).first()
    profile.logo_url = "noturl"
    db_session.add(profile)
    with pytest.raises(StatementError):
        db_session.commit()
    db_session.rollback()


def test_validate_name(db_session, new_organization):
    assert Profile.validate_name_candidate(new_organization.profile.name) == 'org'


def test_user_avatar(db_session, user_twoflower, user_rincewind):
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
    assert user_rincewind.avatar == ImgeeFurl('https://images.example.com/p.jpg')


def test_suspended_user_private_profile(db_session, user_wolfgang):
    """Suspending a user will mark their profile as private."""
    # Ensure column defaults are set (Profile.state)
    db_session.commit()

    # Profile cannot be public until the user has verified contact info
    with pytest.raises(StateTransitionError):
        user_wolfgang.profile.make_public()

    # Add an email address to meet the criteria for having verified contact info
    user_wolfgang.add_email('wolfgang@example.org')

    # Make profile public and confirm
    user_wolfgang.profile.make_public()
    assert user_wolfgang.profile.state.PUBLIC

    # Suspend the user. Profile can now be made private, but cannot be made public
    user_wolfgang.mark_suspended()
    # Commit to refresh profile.is_active column property
    db_session.commit()

    assert user_wolfgang.profile.state.PUBLIC
    user_wolfgang.profile.make_private()
    assert not user_wolfgang.profile.state.PUBLIC
    assert user_wolfgang.profile.state.PRIVATE

    # A suspended user's profile cannot be made public
    with pytest.raises(StateTransitionError):
        user_wolfgang.profile.make_public()
