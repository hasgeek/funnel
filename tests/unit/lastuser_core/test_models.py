# -*- coding: utf-8 -*-
from os import environ

from funnel import db
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestModels(TestDatabaseFixture):
    def test_merge_users(self):
        """
        Test to verify merger of user accounts and return new user
        """
        # Scenario 1: if first user's created_at date younger than second user's created_at
        crusoe = self.fixtures.crusoe
        bathound = models.User(username="bathound", fullname="Bathound")
        db.session.add(bathound)
        db.session.commit()
        with self.app.test_request_context('/'):
            merged = models.merge_users(crusoe, bathound)
            self.assertEqual(merged, crusoe)
            self.assertIsInstance(merged, models.User)
            # because the logic is to merge into older account
            self.assertEqual(crusoe.status, 0)
            self.assertEqual(bathound.status, 2)

        # Scenario 1: if second user's created_at date older than first user 's created_at
        tyrion = models.User(username='tyrion', fullname="Tyrion Lannister")
        db.session.add(tyrion)
        db.session.commit()
        subramanian = models.User(username='subramanian', fullname="Tyrion Subramanian")
        db.session.add(subramanian)
        db.session.commit()
        with self.app.test_request_context('/'):
            merged = models.merge_users(subramanian, tyrion)
            self.assertEqual(merged, tyrion)
            self.assertIsInstance(merged, models.User)
            # because the logic is to merge into older account
            self.assertEqual(tyrion.status, 0)
            self.assertEqual(subramanian.status, 2)

    def test_getuser(self):
        """
        Test for retrieving username by prepending @
        """
        # scenario 1: with @ starting in name and extid
        crusoe = self.fixtures.crusoe
        service_twitter = 'twitter'
        oauth_token = environ.get('TWITTER_OAUTH_TOKEN')
        oauth_token_type = 'Bearer'  # NOQA: S105
        externalid = models.UserExternalId(
            service=service_twitter,
            user=crusoe,
            userid=crusoe.email.email,
            username=crusoe.username,
            oauth_token=oauth_token,
            oauth_token_type=oauth_token_type,
        )
        db.session.add(externalid)
        db.session.commit()
        result1 = models.getuser('@crusoe')
        self.assertIsInstance(result1, models.User)
        self.assertEqual(result1, crusoe)

        # scenario 2: with @ in name and not extid
        d_email = 'd@dothraki.vly'
        daenerys = models.User(
            username='daenerys', fullname="Daenerys Targaryen", email=d_email
        )
        daenerys_email = models.UserEmail(email=d_email, user=daenerys)
        db.session.add_all([daenerys, daenerys_email])
        db.session.commit()
        result2 = models.getuser(d_email)
        self.assertIsInstance(result2, models.User)
        self.assertEqual(result2, daenerys)
        result3 = models.getuser('@daenerys')
        self.assertIsNone(result3)

        # scenario 3: with no @ starting in name, check by UserEmailClaim
        j_email = 'jonsnow@nightswatch.co.uk'
        jonsnow = models.User(username='jonsnow', fullname="Jon Snow")
        jonsnow_email_claimed = models.UserEmailClaim(email=j_email, user=jonsnow)
        db.session.add_all([jonsnow, jonsnow_email_claimed])
        db.session.commit()
        result4 = models.getuser(j_email)
        self.assertIsInstance(result4, models.User)
        self.assertEqual(result4, jonsnow)

        # scenario 5: with no @ anywhere in name, fetch username
        arya = models.User(username='arya', fullname="Arya Stark")
        db.session.add(arya)
        db.session.commit()
        result5 = models.getuser('arya')
        self.assertEqual(result5, arya)

        # scenario 6: with no starting with @ name and no UserEmailClaim or UserEmail
        cersei = models.User(username='cersei', fullname="Cersei Lannister")
        db.session.add(cersei)
        db.session.commit()
        result6 = models.getuser('cersei@thelannisters.co.uk')
        self.assertIsNone(result6)

    def test_getextid(self):
        """
        Test for retrieving user given service and userid
        """
        crusoe = self.fixtures.crusoe
        email = crusoe.email.email
        service_facebook = 'facebook'

        externalid = models.UserExternalId(  # NOQA: S106
            service=service_facebook,
            user=crusoe,
            userid=crusoe.email.email,
            username=crusoe.email.email,
            oauth_token=environ.get('FACEBOOK_OAUTH_TOKEN'),
            oauth_token_type='Bearer',
        )

        db.session.add(externalid)
        db.session.commit()
        result = models.getextid(service_facebook, userid=email)
        self.assertIsInstance(result, models.UserExternalId)
        assert '<UserExternalId {service}:{username} of {user}>'.format(
            service=service_facebook, username=email, user=repr(crusoe)[1:-1]
        ) in repr(result)
