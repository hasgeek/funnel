"""Tests for UserExternalId model."""

import pytest

from funnel import models

from .db_test import TestDatabaseFixture


class TestUserExternalId(TestDatabaseFixture):
    def test_userexternalid(self) -> None:
        """Test for creating an instance of UserExternalId."""
        crusoe = self.fixtures.crusoe
        service = 'google'
        oauth_token = '196461869-pPh2cPTnlqGHcJBcyQ4CR407d1j5LY4OdbhNQuvX'  # nosec
        oauth_token_type = 'Bearer'  # nosec
        result = models.AccountExternalId(
            service=service,
            account=crusoe,
            userid=str(crusoe.email),
            username=str(crusoe.email),
            oauth_token=oauth_token,
            oauth_token_type=oauth_token_type,
        )
        assert isinstance(result, models.AccountExternalId)
        assert f'<UserExternalId {service}:{crusoe.email} of {crusoe!r}>' in repr(
            result
        )

    def test_userexternalid_get(self) -> None:
        """Retrieve a UserExternalId given a service and userid or username."""
        service = 'twitter'
        # scenario 1: when neither userid nor username is passed
        with pytest.raises(TypeError):
            models.AccountExternalId.get(service)  # type: ignore[call-overload]

        crusoe = self.fixtures.crusoe
        oauth_token = 'this-is-a-sample-token'  # nosec
        oauth_token_type = 'Bearer'  # nosec
        externalid = models.AccountExternalId(
            service=service,
            account=crusoe,
            userid=str(crusoe.email),
            username=str(crusoe.email),
            oauth_token=oauth_token,
            oauth_token_type=oauth_token_type,
        )
        self.db_session.add(externalid)
        self.db_session.commit()
        # scenario 2: when userid is passed
        get_by_userid = models.AccountExternalId.get(
            service=service, userid=str(crusoe.email)
        )
        assert isinstance(get_by_userid, models.AccountExternalId)
        assert f'<UserExternalId {service}:{crusoe.email} of {crusoe!r}>' in repr(
            get_by_userid
        )
        # scenario 3: when username is passed
        get_by_username = models.AccountExternalId.get(
            service=service, username=str(crusoe.email)
        )
        assert isinstance(get_by_username, models.AccountExternalId)
        assert f'<UserExternalId {service}:{crusoe.email} of {crusoe!r}>' in repr(
            get_by_username
        )
