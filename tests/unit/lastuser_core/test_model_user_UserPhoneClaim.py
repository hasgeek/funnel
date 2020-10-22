from funnel import db
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestUserPhoneClaim(TestDatabaseFixture):
    def test_userphoneclaim(self):
        """Test for creation of UserPhoneClaim instance."""
        phone = '9123456780'
        result = models.UserPhoneClaim(phone)
        self.assertIsInstance(result, models.UserPhoneClaim)
        self.assertEqual(result.phone, phone)

    def test_userphoneclaim_all(self):
        """Test for retrieving all instances of UserPhoneClaim given a phone number."""
        crusoe = self.fixtures.crusoe
        oakley = self.fixtures.oakley
        phone = '9191919191'
        claim_by_crusoe = models.UserPhoneClaim(phone=phone, user=crusoe)
        claim_by_oakley = models.UserPhoneClaim(phone=phone, user=oakley)
        db.session.add(claim_by_crusoe, claim_by_oakley)
        db.session.commit()
        result = models.UserPhoneClaim.all(phone)
        self.assertIsInstance(result, list)
        self.assertCountEqual(result, [claim_by_crusoe, claim_by_oakley])

    def test_userphoneclaim_get(self):
        """Retrieve UserPhoneClaim instances given phone number and a user."""
        snow = models.User(username='', fullname='President Coriolanus Snow')
        phone = '9191919191'
        phone_claim = models.UserPhoneClaim(phone=phone, user=snow)
        db.session.add(phone_claim)
        db.session.commit()
        result = models.UserPhoneClaim.get_for(user=snow, phone=phone)
        self.assertIsInstance(result, models.UserPhoneClaim)
        self.assertEqual(result.phone, phone)
        self.assertEqual(result.user, snow)

    def test_userphoneclaim_unicode(self):
        """Test for verifying that UserPhoneClaim instance returns phone as string."""
        haymitch = models.User(username='haymitch', fullname='Haymitch Abernathy')
        phone = '9191919191'
        phone_claim = models.UserPhoneClaim(phone=phone, user=haymitch)
        db.session.add(phone_claim)
        db.session.commit()
        result = str(models.UserPhoneClaim(phone=phone))
        self.assertIsInstance(result, str)
        assert phone in result

    def test_userphoneclaim_permissions(self):
        """Verify that user has verify permission on a UserPhoneClaim instance."""
        coin = models.User(username='coin', fullname='President Alma Coin')
        phone = '9191919191'
        phone_claim = models.UserPhoneClaim(phone=phone, user=coin)
        permissions_expected = ['verify']
        result = phone_claim.permissions(coin)
        self.assertIsInstance(result, set)
        permissions_received = []
        for each in result:
            permissions_received.append(each)
        self.assertCountEqual(permissions_expected, permissions_received)
