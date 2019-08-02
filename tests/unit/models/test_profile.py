# -*- coding: utf-8 -*-

from sqlalchemy.exc import StatementError

from furl import furl
import pytest


class TestProfile(object):
    def test_profile_urltype_valid(self, test_client, test_db, new_profile):
        new_profile.logo_url = "https://hasgeek.com"
        test_db.session.add(new_profile)
        test_db.session.commit()
        assert isinstance(new_profile.logo_url, furl)
        assert new_profile.logo_url.url == "https://hasgeek.com"

    def test_profile_urltype_invalid(self, test_client, test_db, new_profile):
        new_profile.logo_url = "noturl"
        test_db.session.add(new_profile)
        with pytest.raises(StatementError):
            test_db.session.commit()
        test_db.session.rollback()

    def test_reserved_name(self, test_client, test_db, new_profile):
        new_profile.title = "Proposals"
        new_profile.make_name()
        # because `proposals` is in reserved name list, `make_name` will
        # try to generate a name for it starting with suffixing it with 2.
        assert new_profile.name == "proposals2"
