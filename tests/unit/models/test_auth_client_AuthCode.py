"""Tests for AuthCode model."""

from .test_db import TestDatabaseFixture


class TestAuthCode(TestDatabaseFixture):
    def test_authcode_init(self, models) -> None:
        """Test to verify creation of AuthCode instance."""
        crusoe = self.fixtures.crusoe
        auth_client = self.fixtures.auth_client
        auth_code = models.AuthCode(
            user=crusoe,
            auth_client=auth_client,
            redirect_uri='http://batdogadventures.com/fun',
            scope='id',
        )
        # code redirect_uri, used
        self.db_session.add(auth_code)
        self.db_session.commit()
        result = models.AuthCode.all_for(user=crusoe).one_or_none()
        assert isinstance(result, models.AuthCode)
        assert result.auth_client == auth_client
        assert result.user == crusoe

    def test_authcode_is_valid(self, models) -> None:
        """Test to verify if a AuthCode instance is valid."""
        oakley = self.fixtures.oakley
        auth_client = self.fixtures.auth_client
        auth_code = models.AuthCode(
            user=oakley,
            auth_client=auth_client,
            used=True,
            redirect_uri='http://batdogadventures.com/fun',
            scope='email',
        )
        self.db_session.add(auth_code)
        self.db_session.commit()

        # Scenario 1: When code has not been used
        unused_code_status = models.AuthCode.all_for(user=oakley).one().is_valid()
        assert not unused_code_status

        # Scenario 2: When code has been used
        auth_code.used = False
        self.db_session.commit()
        used_code_status = models.AuthCode.all_for(user=oakley).one().is_valid()
        assert used_code_status
