"""Tests for UserEmail model."""

import base58
import pytest

from funnel import models

from .test_db import TestDatabaseFixture


class TestUserEmail(TestDatabaseFixture):
    def test_useremail(self) -> None:
        """Test for verifying creation of UserEmail object."""
        oakley = self.fixtures.oakley
        oakley_new_email = models.user.UserEmail(user=oakley, email='oakley@batdog.ca')
        assert isinstance(oakley_new_email, models.user.UserEmail)

    def test_useremail_get(self) -> None:
        """Test for `UserEmail.get` against email, blake2b160 digest and hex hash."""
        crusoe = self.fixtures.crusoe
        email = crusoe.email.email
        blake2b160 = models.email_address.email_blake2b160_hash(email)
        email_hash = base58.b58encode(blake2b160).decode()

        # scenario 1: when no parameters are passed
        with pytest.raises(TypeError):
            models.UserEmail.get()  # type: ignore[call-overload]

        # scenario 2: when email is passed
        get_by_email = models.UserEmail.get(email=email)
        assert isinstance(get_by_email, models.UserEmail)
        assert get_by_email.user == crusoe

        # scenario 3: when blake2b160 is passed
        get_by_b2hash = models.UserEmail.get(blake2b160=blake2b160)
        assert isinstance(get_by_b2hash, models.UserEmail)
        assert get_by_b2hash.user == crusoe

        # secnario 4: when email_hash is passed
        get_by_email_hash = models.UserEmail.get(email_hash=email_hash)
        assert isinstance(get_by_email_hash, models.UserEmail)
        assert get_by_email_hash.user == crusoe

    def test_useremail_str(self) -> None:
        """Test for verifying email is returned in unicode format."""
        crusoe = self.fixtures.crusoe
        assert crusoe.email.email == str(crusoe.email)

    def test_useremail_email(self) -> None:
        """Test for verifying UserEmail instance's email property."""
        oakley = self.fixtures.oakley
        email = 'oakley@batdogs.ca'
        oakley_new_email = models.UserEmail(user=oakley, email=email)
        result = oakley_new_email.email
        assert isinstance(result, str)
        assert email == result
