"""Tests for UserPhone model."""

from funnel import models

from .test_db import TestDatabaseFixture


class TestUserPhone(TestDatabaseFixture):
    def test_userphone(self) -> None:
        """Test for verifying creation of UserPhone instance."""
        phone = '+918123456789'
        result = models.UserPhone(user=self.fixtures.crusoe, phone=phone)
        assert isinstance(result, models.UserPhone)

    def test_userphone_get(self) -> None:
        """Test for verifying UserPhone's get given a phone number."""
        crusoe = self.fixtures.crusoe
        phone = '+918123456789'
        result = models.UserPhone.get(phone)
        assert isinstance(result, models.UserPhone)
        assert result.user == crusoe
        assert result.phone == phone

    def test_userphone_unicode(self) -> None:
        """Test that `str(UserPhone)` returns phone number as a string."""
        phone = '+918123456789'
        result = str(models.UserPhone(user=self.fixtures.crusoe, phone=phone))
        assert isinstance(result, str)
        assert result == phone
