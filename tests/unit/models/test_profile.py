from sqlalchemy.exc import StatementError

from furl import furl
import pytest

from funnel.models import Profile


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
