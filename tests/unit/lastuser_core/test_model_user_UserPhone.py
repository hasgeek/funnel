import funnel.models as models

from .test_db import TestDatabaseFixture


class TestUserPhone(TestDatabaseFixture):
    def test_userphone(self):
        """Test for verifying creationg of UserPhone instance."""
        phone = "+987645321"
        result = models.UserPhone(phone=phone)
        self.assertIsInstance(result, models.UserPhone)

    def test_userphone_get(self):
        """Test for verifying UserPhone's get given a phone number."""
        crusoe = self.fixtures.crusoe
        phone = '+8080808080'
        result = models.UserPhone.get(phone)
        self.assertIsInstance(result, models.UserPhone)
        self.assertEqual(result.user, crusoe)
        self.assertEqual(result.phone, phone)

    def test_userphone_unicode(self):
        """Test that `str(UserPhone)` returns phone number as a string."""
        phone = '+8080808080'
        result = str(models.UserPhone(phone))
        self.assertIsInstance(result, str)
        self.assertEqual(result, phone)
