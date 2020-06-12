from funnel.models.email_address import email_blake2b160_hash
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestUserEmail(TestDatabaseFixture):
    def test_useremail(self):
        """
        Test for verifying creation of UserEmail object
        """
        oakley = self.fixtures.oakley
        oakley_new_email = models.user.UserEmail(user=oakley, email='oakley@batdog.ca')
        self.assertIsInstance(oakley_new_email, models.user.UserEmail)

    def test_useremail_get(self):
        """
        Test for verifying UserEmail's get that should return a UserEmail object with matching email or md5sum
        """
        crusoe = self.fixtures.crusoe
        email = crusoe.email.email
        blake2b160 = email_blake2b160_hash(email)
        # scenario 1: when no parameters are passed
        with self.assertRaises(TypeError):
            models.UserEmail.get()

        # scenario 2: when email is passed
        get_by_email = models.UserEmail.get(email=email)
        self.assertIsInstance(get_by_email, models.UserEmail)
        self.assertEqual(get_by_email.user, crusoe)

        # scenario 3: when blake2b160 is passed
        get_by_hash = models.UserEmail.get(blake2b160=blake2b160)
        self.assertIsInstance(get_by_hash, models.UserEmail)
        self.assertEqual(get_by_hash.user, crusoe)

    def test_useremail_str(self):
        """
        Test for verifying email is returned in unicode format
        """
        crusoe = self.fixtures.crusoe
        assert crusoe.email.email == str(crusoe.email)

    def test_useremail_email(self):
        """
        Test for verifying UserEmail instance's email property
        """
        oakley = self.fixtures.oakley
        email = 'oakley@batdogs.ca'
        oakley_new_email = models.UserEmail(user=oakley, email=email)
        result = oakley_new_email.email
        self.assertIsInstance(result, str)
        self.assertEqual(email, result)
