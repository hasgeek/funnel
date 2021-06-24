from datetime import timedelta

import pytest

from coaster.utils import buid, utcnow
import funnel.models as models

sample_user_agent = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like'
    ' Gecko) Chrome/49.0.2623.110 Safari/537.36'
)


def test_usersession_init(db_session):
    """Test to verify the creation of UserSession instance."""
    result = models.UserSession()
    assert isinstance(result, models.UserSession)


def test_usersession_has_sudo(db_session, user_twoflower):
    """Test to set sudo and test if UserSession instance has_sudo."""
    another_user_session = models.UserSession(
        user=user_twoflower,
        ipaddr='192.168.1.1',
        user_agent=sample_user_agent,
        accessed_at=utcnow(),
    )
    another_user_session.set_sudo()
    db_session.add(another_user_session)
    db_session.commit()
    assert another_user_session.has_sudo is True


def test_usersession_revoke(db_session, user_twoflower):
    """Test to revoke on UserSession instance."""
    yet_another_usersession = models.UserSession(
        user=user_twoflower,
        ipaddr='192.168.1.1',
        user_agent=sample_user_agent,
        accessed_at=utcnow(),
    )
    yet_another_usersession.revoke()
    result = models.UserSession.get(yet_another_usersession.buid)
    assert result.revoked_at is not None


def test_usersession_get(db_session, user_twoflower):
    """Test for verifying UserSession's get method."""
    twoflower_buid = buid()
    twoflower_session = models.UserSession(
        user=user_twoflower,
        ipaddr='192.168.1.2',
        buid=twoflower_buid,
        user_agent=sample_user_agent,
        accessed_at=utcnow(),
    )
    result = twoflower_session.get(buid=twoflower_buid)
    assert isinstance(result, models.UserSession)
    assert result.user_id == user_twoflower.id


def test_usersession_active_sessions(db_session, user_twoflower):
    """Test for verifying UserSession's active_sessions."""
    twoflower_session = models.UserSession(
        user=user_twoflower,
        ipaddr='192.168.1.3',
        buid=buid(),
        user_agent=sample_user_agent,
        accessed_at=utcnow(),
    )
    assert isinstance(user_twoflower.active_user_sessions.all(), list)
    assert user_twoflower.active_user_sessions.all() == [twoflower_session]


def test_usersession_authenticate(db_session, user_dibbler):
    """Test to verify authenticate method on UserSession."""
    dibbler_session = models.UserSession(
        user=user_dibbler,
        ipaddr='192.168.1.4',
        user_agent=sample_user_agent,
        accessed_at=utcnow(),
    )
    db_session.add(dibbler_session)
    db_session.commit()
    result = models.UserSession.authenticate(dibbler_session.buid)
    assert isinstance(result, models.UserSession)
    assert result == dibbler_session

    # Now manipulate the session to make it invalid
    # 1. More than a year since last access, so it's expired
    dibbler_session.accessed_at = utcnow() - timedelta(days=1000)
    db_session.commit()
    # By default, expired sessions raise an exception
    with pytest.raises(models.UserSessionExpired):
        models.UserSession.authenticate(dibbler_session.buid)
    # However, silent mode simply returns None
    assert models.UserSession.authenticate(dibbler_session.buid, silent=True) is None

    # 2. Revoked session (taking priority over expiry)
    dibbler_session.accessed_at = utcnow()
    dibbler_session.revoked_at = utcnow()
    db_session.commit()
    with pytest.raises(models.UserSessionRevoked):
        models.UserSession.authenticate(dibbler_session.buid)
    # Again, silent mode simply returns None
    assert models.UserSession.authenticate(dibbler_session.buid, silent=True) is None


def test_usersession_authenticate_suspended_user(db_session, user_dibbler):
    """Test to verify authenticate method on UserSession with a suspended user."""
    dibbler_session = models.UserSession(
        user=user_dibbler,
        ipaddr='192.168.1.4',
        user_agent=sample_user_agent,
        accessed_at=utcnow(),
    )
    db_session.add(dibbler_session)
    db_session.commit()
    result = models.UserSession.authenticate(dibbler_session.buid)
    assert isinstance(result, models.UserSession)
    assert result == dibbler_session

    # Now suspend the user
    user_dibbler.mark_suspended()
    db_session.commit()
    with pytest.raises(models.UserSessionInactiveUser) as exc_info:
        models.UserSession.authenticate(dibbler_session.buid)
    assert exc_info.value.args[0] == dibbler_session
    assert exc_info.value.args[0].user == user_dibbler
    assert not user_dibbler.state.ACTIVE
    assert user_dibbler.state.SUSPENDED
    # Again, silent mode simply returns None
    assert models.UserSession.authenticate(dibbler_session.buid, silent=True) is None
