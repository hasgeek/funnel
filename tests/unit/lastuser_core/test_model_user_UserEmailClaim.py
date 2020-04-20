# -*- coding: utf-8 -*-

from lastuserapp import db
import lastuser_core.models as models

from coaster.utils import md5sum

from .test_db import TestDatabaseFixture


class TestUserEmailClaim(TestDatabaseFixture):
    def test_useremailclaim(self):
        crusoe = self.fixtures.crusoe
        domain = 'batdogs.ca'
        new_email = 'crusoe@' + domain
        emd5sum = md5sum(new_email)
        result = models.UserEmailClaim(email=new_email, user=crusoe)
        db.session.add(result)
        db.session.commit()
        self.assertIsInstance(result, models.UserEmailClaim)
        self.assertEqual(emd5sum, result.md5sum)
        self.assertEqual(domain, result.domain)
        self.assertEqual(crusoe, result.user)
        assert '<UserEmailClaim {email} of {user}>'.format(
            email=new_email, user=repr(crusoe)[1:-1]
        ) in (repr(result))

    def test_useremailclaim_permissions(self):
        """
        Test for verifying whether user has verify permission on a UserEmailClaim instance
        """
        crusoe = self.fixtures.crusoe
        email = 'crusoe@batdogs.ca'
        email_claim = models.UserEmailClaim(email=email, user=crusoe)
        permissions_expected = ['verify']
        result = email_claim.permissions(crusoe)
        self.assertIsInstance(result, set)
        permissions_received = []
        for each in result:
            permissions_received.append(each)
        self.assertCountEqual(permissions_expected, permissions_received)

    def test_useremailclaim_get(self):
        """
        Test for retrieving a UserEmailClaim instance given a user
        """

        katnis = models.User(username='katnis', fullname='Katnis Everdeen')
        email = 'katnis@hungergames.org'
        email_claim = models.UserEmailClaim(email=email, user=katnis)
        db.session.add(email_claim)
        db.session.commit()
        result = models.UserEmailClaim.get_for(user=katnis, email=email)
        self.assertIsInstance(result, models.UserEmailClaim)
        self.assertEqual(result.email, email)
        self.assertEqual(result.user, katnis)

    def test_useremailclaim_all(self):
        """
        Test for retrieving all UserEmailClaim instances given an email address
        """
        gail = models.User(username='gail', fullname='Gail Hawthorne')
        peeta = models.User(username='peeta', fullname='Peeta Mallark')
        email = 'gail@district7.gov'
        claim_by_gail = models.UserEmailClaim(email=email, user=gail)
        claim_by_peeta = models.UserEmailClaim(email=email, user=peeta)
        db.session.add(claim_by_gail)
        db.session.add(claim_by_peeta)
        db.session.commit()
        result = models.UserEmailClaim.all(email)
        self.assertCountEqual(set(result), {claim_by_gail, claim_by_peeta})

    def test_useremailclaim_email(self):
        """
        Test for verifying UserEmailClaim email property
        """
        effie = models.User(username='effie', fullname='Miss. Effie Trinket')
        email = 'effie@hungergames.org'
        claim_by_effie = models.UserEmailClaim(email=email, user=effie)
        self.assertIsInstance(claim_by_effie.email, str)
        self.assertEqual(claim_by_effie.email, email)
