import funnel.models as models

from .test_db import TestDatabaseFixture


class TestUserEmailClaim(TestDatabaseFixture):
    def test_useremailclaim(self):
        crusoe = self.fixtures.crusoe
        new_email = 'crusoe@batdogs.ca'
        result = models.UserEmailClaim(user=crusoe, email=new_email)
        self.db_session.add(result)
        self.db_session.commit()
        assert isinstance(result, models.UserEmailClaim)
        assert crusoe == result.user
        assert '<UserEmailClaim {email} of {user}>'.format(
            email=new_email, user=repr(crusoe)[1:-1]
        ) in (repr(result))

    def test_useremailclaim_permissions(self):
        """Test that user has verify permission on a UserEmailClaim instance."""
        crusoe = self.fixtures.crusoe
        email = 'crusoe@batdogs.ca'
        email_claim = models.UserEmailClaim(user=crusoe, email=email)
        permissions_expected = {'verify'}
        permissions_received = email_claim.permissions(crusoe)
        assert permissions_expected == permissions_received

    def test_useremailclaim_get(self):
        """Test for retrieving a UserEmailClaim instance given a user."""
        katnis = models.User(username='katnis', fullname='Katnis Everdeen')
        email = 'katnis@hungergames.org'
        email_claim = models.UserEmailClaim(user=katnis, email=email)
        self.db_session.add(email_claim)
        self.db_session.commit()
        result = models.UserEmailClaim.get_for(user=katnis, email=email)
        assert isinstance(result, models.UserEmailClaim)
        assert result.email == email
        assert result.user == katnis

    def test_useremailclaim_all(self):
        """Test for retrieving all UserEmailClaim instances given an email address."""
        gail = models.User(username='gail', fullname='Gail Hawthorne')
        peeta = models.User(username='peeta', fullname='Peeta Mallark')
        email = 'gail@district7.gov'
        claim_by_gail = models.UserEmailClaim(user=gail, email=email)
        claim_by_peeta = models.UserEmailClaim(user=peeta, email=email)
        self.db_session.add(claim_by_gail)
        self.db_session.add(claim_by_peeta)
        self.db_session.commit()
        result = models.UserEmailClaim.all(email)
        assert set(result) == {claim_by_gail, claim_by_peeta}

    def test_useremailclaim_email(self):
        """Test for verifying UserEmailClaim email property."""
        effie = models.User(username='effie', fullname='Miss. Effie Trinket')
        email = 'effie@hungergames.org'
        claim_by_effie = models.UserEmailClaim(user=effie, email=email)
        assert isinstance(claim_by_effie.email, str)
        assert claim_by_effie.email == email
