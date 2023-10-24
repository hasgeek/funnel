"""Tests for AccountEmailClaim model."""

from funnel import models

from .db_test import TestDatabaseFixture


class TestUserEmailClaim(TestDatabaseFixture):
    def test_useremailclaim(self) -> None:
        crusoe = self.fixtures.crusoe
        new_email = 'crusoe@batdogs.ca'
        result = models.AccountEmailClaim(account=crusoe, email=new_email)
        self.db_session.add(result)
        self.db_session.commit()
        assert isinstance(result, models.AccountEmailClaim)
        assert crusoe == result.account
        assert f'<AccountEmailClaim {new_email} of {crusoe!r}>' in (repr(result))

    def test_useremailclaim_get(self) -> None:
        """Test for retrieving an AccountEmailClaim instance given a user."""
        katnis = models.User(username='katnis', fullname='Katnis Everdeen')
        email = 'katnis@hungergames.org'
        email_claim = models.AccountEmailClaim(account=katnis, email=email)
        self.db_session.add(email_claim)
        self.db_session.commit()
        result = models.AccountEmailClaim.get_for(account=katnis, email=email)
        assert isinstance(result, models.AccountEmailClaim)
        assert result.email == email
        assert result.account == katnis

    def test_useremailclaim_all(self) -> None:
        """Test for retrieving all AccountEmailClaim instances given email address."""
        gail = models.User(username='gail', fullname='Gail Hawthorne')
        peeta = models.User(username='peeta', fullname='Peeta Mallark')
        email = 'gail@district7.gov'
        claim_by_gail = models.AccountEmailClaim(account=gail, email=email)
        claim_by_peeta = models.AccountEmailClaim(account=peeta, email=email)
        self.db_session.add(claim_by_gail)
        self.db_session.add(claim_by_peeta)
        self.db_session.commit()
        result = models.AccountEmailClaim.all(email)
        assert set(result) == {claim_by_gail, claim_by_peeta}

    def test_useremailclaim_email(self) -> None:
        """Test for verifying AccountEmailClaim email property."""
        effie = models.User(username='effie', fullname='Miss. Effie Trinket')
        email = 'effie@hungergames.org'
        claim_by_effie = models.AccountEmailClaim(account=effie, email=email)
        assert isinstance(claim_by_effie.email, str)
        assert claim_by_effie.email == email
