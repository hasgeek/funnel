from datetime import timedelta

import pytest

from coaster.utils import buid, utcnow
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestUser(TestDatabaseFixture):
    def test_usersession_init(self):
        """Test to verify the creation of UserSession instance."""
        result = models.UserSession()
        assert isinstance(result, models.UserSession)

    def test_usersession_has_sudo(self):
        """Test to set sudo and test if UserSession instance has_sudo."""
        crusoe = self.fixtures.crusoe
        another_user_session = models.UserSession(
            user=crusoe,
            ipaddr='192.168.1.1',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        another_user_session.set_sudo()
        self.db_session.add(another_user_session)
        self.db_session.commit()
        assert another_user_session.has_sudo is True

    def test_usersession_revoke(self):
        """Test to revoke on UserSession instance."""
        crusoe = self.fixtures.crusoe
        yet_another_usersession = models.UserSession(
            user=crusoe,
            ipaddr='192.168.1.1',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        yet_another_usersession.revoke()
        result = models.UserSession.get(yet_another_usersession.buid)
        assert result.revoked_at is not None

    def test_usersession_get(self):
        """Test for verifying UserSession's get method."""
        oakley = self.fixtures.oakley
        oakley_buid = buid()
        oakley_session = models.UserSession(
            user=oakley,
            ipaddr='192.168.1.2',
            buid=oakley_buid,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        result = oakley_session.get(buid=oakley_buid)
        assert isinstance(result, models.UserSession)
        assert result.user_id == oakley.id

    def test_usersession_active_sessions(self):
        """Test for verifying UserSession's active_sessions."""
        piglet = self.fixtures.piglet
        piglet_session = models.UserSession(
            user=piglet,
            ipaddr='192.168.1.3',
            buid=buid(),
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        assert isinstance(piglet.active_user_sessions.all(), list)
        assert piglet.active_user_sessions.all() == [piglet_session]

    def test_usersession_authenticate(self):
        """Test to verify authenticate method on UserSession."""
        chandler = models.User(username='chandler', fullname='Chandler Bing')
        chandler_session = models.UserSession(
            user=chandler,
            ipaddr='192.168.1.4',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        self.db_session.add(chandler)
        self.db_session.add(chandler_session)
        self.db_session.commit()
        result = models.UserSession.authenticate(chandler_session.buid)
        assert isinstance(result, models.UserSession)
        assert result == chandler_session

        # Now manipulate the session to make it invalid
        # 1. More than a year since last access, so it's expired
        chandler_session.accessed_at = utcnow() - timedelta(days=1000)
        self.db_session.commit()
        # By default, expired sessions raise an exception
        with pytest.raises(models.UserSessionExpired):
            models.UserSession.authenticate(chandler_session.buid)
        # However, silent mode simply returns None
        assert (
            models.UserSession.authenticate(chandler_session.buid, silent=True) is None
        )

        # 2. Revoked session (taking priority over expiry)
        chandler_session.accessed_at = utcnow()
        chandler_session.revoked_at = utcnow()
        self.db_session.commit()
        with pytest.raises(models.UserSessionRevoked):
            models.UserSession.authenticate(chandler_session.buid)
        # Again, silent mode simply returns None
        assert (
            models.UserSession.authenticate(chandler_session.buid, silent=True) is None
        )
