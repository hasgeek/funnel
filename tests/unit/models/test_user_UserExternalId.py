"""Tests for UserExternalId model."""

import pytest

from funnel import models

from .test_db import TestDatabaseFixture


class TestUserExternalId(TestDatabaseFixture):
    def test_userexternalid(self) -> None:
        """Test for creating an instance of UserExternalId."""
        crusoe = self.fixtures.crusoe
        service = 'google'
        oauth_token = (
            '196461869-pPh2cPTnlqGHcJBcyQ4CR407d1j5LY4OdbhNQuvX'  # nosec  # noqa: S105
        )
        oauth_token_type = 'Bearer'  # nosec  # noqa: S105
        result = models.UserExternalId(
            service=service,
            user=crusoe,
            userid=crusoe.email.email,
            username=crusoe.email.email,
            oauth_token=oauth_token,
            oauth_token_type=oauth_token_type,
        )
        assert isinstance(result, models.UserExternalId)
        assert f'<UserExternalId {service}:{crusoe.email.email} of {crusoe!r}>' in repr(
            result
        )

    def test_userexternalid_get(self) -> None:
        """Retrieve a UserExternalId given a service and userid or username."""
        service = 'twitter'
        # scenario 1: when neither userid nor username is passed
        with pytest.raises(TypeError):
            models.UserExternalId.get(service)  # type: ignore[call-overload]

        crusoe = self.fixtures.crusoe
        oauth_token = 'this-is-a-sample-token'  # nosec  # noqa: S105
        oauth_token_type = 'Bearer'  # nosec  # noqa: S105
        externalid = models.UserExternalId(
            service=service,
            user=crusoe,
            userid=crusoe.email.email,
            username=crusoe.email.email,
            oauth_token=oauth_token,
            oauth_token_type=oauth_token_type,
        )
        self.db_session.add(externalid)
        self.db_session.commit()
        # scenario 2: when userid is passed
        get_by_userid = models.UserExternalId.get(
            service=service, userid=crusoe.email.email
        )
        assert isinstance(get_by_userid, models.UserExternalId)
        assert f'<UserExternalId {service}:{crusoe.email.email} of {crusoe!r}>' in repr(
            get_by_userid
        )
        # scenario 3: when username is passed
        get_by_username = models.UserExternalId.get(
            service=service, username=crusoe.email.email
        )
        assert isinstance(get_by_username, models.UserExternalId)
        assert f'<UserExternalId {service}:{crusoe.email.email} of {crusoe!r}>' in repr(
            get_by_username
        )
