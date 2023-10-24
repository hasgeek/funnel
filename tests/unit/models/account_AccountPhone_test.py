"""Tests for AccountPhone model."""

from funnel import models

from .db_test import TestDatabaseFixture


class TestUserPhone(TestDatabaseFixture):
    def test_userphone(self) -> None:
        """Test for verifying creation of AccountPhone instance."""
        phone = '+918123456789'
        result = models.AccountPhone(account=self.fixtures.crusoe, phone=phone)
        assert isinstance(result, models.AccountPhone)

    def test_userphone_get(self) -> None:
        """Test for verifying AccountPhone's get given a phone number."""
        crusoe = self.fixtures.crusoe
        phone = '+918123456789'
        result = models.AccountPhone.get(phone)
        assert isinstance(result, models.AccountPhone)
        assert result.account == crusoe
        assert result.phone == phone

    def test_userphone_unicode(self) -> None:
        """Test that `str(AccountPhone)` returns phone number as a string."""
        phone = '+918123456789'
        result = str(models.AccountPhone(account=self.fixtures.crusoe, phone=phone))
        assert isinstance(result, str)
        assert result == phone
