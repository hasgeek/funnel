# -*- coding: utf-8 -*-

from coaster.utils import buid, utcnow
from lastuserapp import db
import lastuser_core.models as models

from .test_db import TestDatabaseFixture


class TestUser(TestDatabaseFixture):
    def test_usersession_init(self):
        """Test to verify the creation of UserSession instance"""
        result = models.UserSession()
        self.assertIsInstance(result, models.UserSession)

    def test_usersession_ua(self):
        """Test to verify user_agent property of UserSession instance"""
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36'
        another_user_session = models.UserSession(user_agent=ua)
        self.assertIsInstance(another_user_session.ua, dict)

    def test_usersession_has_sudo(self):
        """Test to set sudo and test if UserSession instance has_sudo """
        crusoe = self.fixtures.crusoe
        another_user_session = models.UserSession(
            user=crusoe,
            ipaddr='192.168.1.1',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        another_user_session.set_sudo()
        db.session.add(another_user_session)
        db.session.commit()
        self.assertTrue(another_user_session.has_sudo)

    def test_usersession_revoke(self):
        """Test to revoke on UserSession instance"""
        crusoe = self.fixtures.crusoe
        yet_another_usersession = models.UserSession(
            user=crusoe,
            ipaddr='192.168.1.1',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        yet_another_usersession.revoke()
        result = models.UserSession.get(yet_another_usersession.buid)
        self.assertIsNotNone(result.revoked_at)

    def test_usersession_get(self):
        """Test for verifying UserSession's get method"""
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
        self.assertIsInstance(result, models.UserSession)
        self.assertEqual(result.user_id, oakley.id)

    def test_usersession_active_sessions(self):
        "Test for verifying UserSession's active_sessions"
        piglet = self.fixtures.piglet
        piglet_session = models.UserSession(
            user=piglet,
            ipaddr='192.168.1.3',
            buid=buid(),
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        self.assertIsInstance(piglet.active_sessions.all(), list)
        self.assertCountEqual(piglet.active_sessions.all(), [piglet_session])

    def test_usersession_authenticate(self):
        """Test to verify authenticate method on UserSession"""
        chandler = models.User(username='chandler', fullname='Chandler Bing')
        chandler_buid = buid()
        chandler_session = models.UserSession(
            user=chandler,
            ipaddr='192.168.1.4',
            buid=chandler_buid,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
            accessed_at=utcnow(),
        )
        db.session.add(chandler)
        db.session.add(chandler_session)
        db.session.commit()
        result = models.UserSession.authenticate(chandler_buid)
        self.assertIsInstance(result, models.UserSession)
        self.assertEqual(result, chandler_session)
