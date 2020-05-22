from sqlalchemy.exc import StatementError

from furl import furl
import pytest

from funnel.models import Profile


class TestProfile(object):
    def test_profile_urltype_valid(self, test_db, new_organization):
        profile = Profile.query.filter_by(id=new_organization.profile.id).first()
        assert profile.name == 'test-org'
        profile.logo_url = "https://hasgeek.com"
        test_db.session.add(profile)
        test_db.session.commit()
        assert isinstance(profile.logo_url, furl)
        assert profile.logo_url.url == "https://hasgeek.com"

    def test_profile_urltype_invalid(self, test_db, new_organization):
        profile = Profile.query.filter_by(id=new_organization.profile.id).first()
        profile.logo_url = "noturl"
        test_db.session.add(profile)
        with pytest.raises(StatementError):
            test_db.session.commit()
        test_db.session.rollback()

    def test_validate_name(self, test_db, new_organization):
        assert Profile.validate_name_candidate(new_organization.profile.name) == 'org'
