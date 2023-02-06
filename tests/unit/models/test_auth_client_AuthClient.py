"""Tests for AuthClient model."""

import pytest

from coaster.utils import utcnow
from funnel import models

from .test_db import TestDatabaseFixture


class TestClient(TestDatabaseFixture):
    def test_client_secret_is(self) -> None:
        """Test for checking if Client's secret is a ClientCredential."""
        auth_client = self.fixtures.auth_client
        cred, secret = models.AuthClientCredential.new(auth_client)
        assert auth_client.secret_is(secret, cred.name)

    def test_client_host_matches(self) -> None:
        """Test that AuthClient.host_matches works with same-site referrer URL."""
        auth_client = self.fixtures.auth_client
        auth_client.redirect_uris = ["http://hasjob.dev:5000"]
        referrer = "http://hasjob.dev:5000/logout"
        assert auth_client.host_matches(referrer)

    def test_client_owner(self) -> None:
        """Test if client's owner is said Organization."""
        owner = self.fixtures.auth_client.owner
        batdog = self.fixtures.batdog
        assert isinstance(owner, models.Organization)
        assert owner == batdog

    def test_client_owner_is(self) -> None:
        """Test if client's owner is a user."""
        auth_client = self.fixtures.auth_client
        crusoe = self.fixtures.crusoe
        assert auth_client.owner_is(crusoe)
        assert not auth_client.owner_is(None)

    def test_client_authtoken_for(self) -> None:
        """Test for retrieving authtoken for confidential auth clients."""
        # scenario 1: for a client that has confidential=True
        auth_client = self.fixtures.auth_client
        crusoe = self.fixtures.crusoe
        result = auth_client.authtoken_for(crusoe)
        client_token = models.AuthToken(
            auth_client=auth_client, user=crusoe, scope='id', validity=0
        )
        self.db_session.add(client_token)
        result = auth_client.authtoken_for(user=crusoe)
        assert client_token == result
        assert isinstance(result, models.AuthToken)
        assert result.user == crusoe

        # scenario 2: for a client that has confidential=False
        varys = models.User(username='varys', fullname='Lord Varys')
        house_lannisters = models.AuthClient(
            title='House of Lannisters',
            confidential=False,
            user=varys,
            website='houseoflannisters.westeros',
        )
        varys_session = models.UserSession(
            user=varys,
            ipaddr='192.168.1.99',
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36'
                ' (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36'
            ),
            accessed_at=utcnow(),
        )
        lannisters_auth_token = models.AuthToken(
            auth_client=house_lannisters,
            user=varys,
            scope='throne',
            validity=0,
            user_session=varys_session,
        )
        self.db_session.add_all(
            [varys, house_lannisters, lannisters_auth_token, varys_session]
        )
        self.db_session.commit()
        result = house_lannisters.authtoken_for(varys, user_session=varys_session)
        assert isinstance(result, models.AuthToken)
        assert "Lord Varys" == result.user.fullname

    def test_client_get(self) -> None:
        """Test for verifying AuthClient's get method."""
        auth_client = self.fixtures.auth_client
        batdog = self.fixtures.batdog
        key = auth_client.buid
        # scenario 1: without key
        with pytest.raises(TypeError):
            models.AuthClient.get()  # type: ignore[call-arg]
        # scenario 2: when given key
        result1 = models.AuthClient.get(buid=key)
        assert isinstance(result1, models.AuthClient)
        assert result1.buid == key
        assert result1.owner == batdog
