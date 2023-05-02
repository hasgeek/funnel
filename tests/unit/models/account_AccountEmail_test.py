"""Tests for AccountEmail model."""

import base58
import pytest

from funnel import models

from .db_test import TestDatabaseFixture


class TestUserEmail(TestDatabaseFixture):
    def test_useremail(self) -> None:
        """Test for verifying creation of AccountEmail object."""
        oakley = self.fixtures.oakley
        oakley_new_email = models.account.AccountEmail(
            account=oakley, email='oakley@batdog.ca'
        )
        assert isinstance(oakley_new_email, models.account.AccountEmail)

    def test_useremail_get(self) -> None:
        """Test for `AccountEmail.get` against email, blake2b160 digest and hex hash."""
        crusoe = self.fixtures.crusoe
        email = crusoe.email.email
        blake2b160 = models.email_address.email_blake2b160_hash(email)
        email_hash = base58.b58encode(blake2b160).decode()

        # scenario 1: when no parameters are passed
        with pytest.raises(TypeError):
            models.AccountEmail.get()  # type: ignore[call-overload]

        # scenario 2: when email is passed
        get_by_email = models.AccountEmail.get(email=email)
        assert isinstance(get_by_email, models.AccountEmail)
        assert get_by_email.account == crusoe

        # scenario 3: when blake2b160 is passed
        get_by_b2hash = models.AccountEmail.get(blake2b160=blake2b160)
        assert isinstance(get_by_b2hash, models.AccountEmail)
        assert get_by_b2hash.account == crusoe

        # secnario 4: when email_hash is passed
        get_by_email_hash = models.AccountEmail.get(email_hash=email_hash)
        assert isinstance(get_by_email_hash, models.AccountEmail)
        assert get_by_email_hash.account == crusoe

    def test_useremail_str(self) -> None:
        """Test for verifying email is returned in unicode format."""
        crusoe = self.fixtures.crusoe
        assert crusoe.email.email == str(crusoe.email)

    def test_useremail_email(self) -> None:
        """Test for verifying AccountEmail instance's email property."""
        oakley = self.fixtures.oakley
        email = 'oakley@batdogs.ca'
        oakley_new_email = models.AccountEmail(account=oakley, email=email)
        result = oakley_new_email.email
        assert isinstance(result, str)
        assert email == result
