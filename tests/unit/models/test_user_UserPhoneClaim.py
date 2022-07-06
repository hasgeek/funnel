"""Test UserPhoneClaim model."""

from funnel import models

from .test_db import TestDatabaseFixture


class TestUserPhoneClaim(TestDatabaseFixture):
    def test_userphoneclaim(self) -> None:
        """Test for creation of UserPhoneClaim instance."""
        phone = '9123456780'
        result = models.UserPhoneClaim(phone)
        assert isinstance(result, models.UserPhoneClaim)
        assert result.phone == phone

    def test_userphoneclaim_all(self) -> None:
        """Test for retrieving all instances of UserPhoneClaim given a phone number."""
        crusoe = self.fixtures.crusoe
        oakley = self.fixtures.oakley
        phone = '9191919191'
        claim_by_crusoe = models.UserPhoneClaim(phone=phone, user=crusoe)
        claim_by_oakley = models.UserPhoneClaim(phone=phone, user=oakley)
        self.db_session.add(claim_by_crusoe, claim_by_oakley)
        self.db_session.commit()
        result = models.UserPhoneClaim.all(phone)
        assert set(result) == {claim_by_crusoe, claim_by_oakley}

    def test_userphoneclaim_get(self) -> None:
        """Retrieve UserPhoneClaim instances given phone number and a user."""
        snow = models.User(username='', fullname='President Coriolanus Snow')
        phone = '9191919191'
        phone_claim = models.UserPhoneClaim(phone=phone, user=snow)
        self.db_session.add(phone_claim)
        self.db_session.commit()
        result = models.UserPhoneClaim.get_for(user=snow, phone=phone)
        assert isinstance(result, models.UserPhoneClaim)
        assert result.phone == phone
        assert result.user == snow

    def test_userphoneclaim_unicode(self) -> None:
        """Test for verifying that UserPhoneClaim instance returns phone as string."""
        haymitch = models.User(username='haymitch', fullname='Haymitch Abernathy')
        phone = '9191919191'
        phone_claim = models.UserPhoneClaim(phone=phone, user=haymitch)
        self.db_session.add(phone_claim)
        self.db_session.commit()
        result = str(models.UserPhoneClaim(phone=phone))
        assert isinstance(result, str)
        assert phone in result
