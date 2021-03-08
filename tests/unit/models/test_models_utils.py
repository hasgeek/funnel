from os import environ

import funnel.models as models

from .test_db import TestDatabaseFixture


class TestModels(TestDatabaseFixture):
    def test_merge_users(self):
        """Test to verify merger of user accounts and return new user."""
        # Scenario 1: if first user's created_at date is older than second user's
        # created_at
        crusoe = self.fixtures.crusoe
        bathound = models.User(username="bathound", fullname="Bathound")
        self.db_session.add(bathound)
        self.db_session.commit()
        with self.app.test_request_context('/'):
            merged = models.merge_users(crusoe, bathound)
            assert merged == crusoe
            assert isinstance(merged, models.User)
            # because the logic is to merge into older account
            assert crusoe.state.ACTIVE
            assert bathound.state.MERGED

        # Scenario 2: if second user's created_at date is older than first user's
        # created_at
        tyrion = models.User(username='tyrion', fullname="Tyrion Lannister")
        self.db_session.add(tyrion)
        self.db_session.commit()
        subramanian = models.User(username='subramanian', fullname="Tyrion Subramanian")
        self.db_session.add(subramanian)
        self.db_session.commit()
        with self.app.test_request_context('/'):
            merged = models.merge_users(subramanian, tyrion)
            assert merged == tyrion
            assert isinstance(merged, models.User)
            # because the logic is to merge into older account
            assert tyrion.state.ACTIVE
            assert subramanian.state.MERGED

    def test_getuser(self):
        """Test for retrieving username by prepending @."""
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
        self.db_session.add(externalid)
        self.db_session.commit()
        result1 = models.getuser('@crusoe')
        assert isinstance(result1, models.User)
        assert result1 == crusoe

        # scenario 2: with @ in name and not extid
        d_email = 'd@dothraki.vly'
        daenerys = models.User(
            username='daenerys', fullname="Daenerys Targaryen", email=d_email
        )
        daenerys_email = models.UserEmail(email=d_email, user=daenerys)
        self.db_session.add_all([daenerys, daenerys_email])
        self.db_session.commit()
        result2 = models.getuser(d_email)
        assert isinstance(result2, models.User)
        assert result2 == daenerys
        result3 = models.getuser('@daenerys')
        assert result3 is None

        # scenario 3: with no @ starting in name, check by UserEmailClaim
        j_email = 'jonsnow@nightswatch.co.uk'
        jonsnow = models.User(username='jonsnow', fullname="Jon Snow")
        jonsnow_email_claimed = models.UserEmailClaim(email=j_email, user=jonsnow)
        self.db_session.add_all([jonsnow, jonsnow_email_claimed])
        self.db_session.commit()
        result4 = models.getuser(j_email)
        assert isinstance(result4, models.User)
        assert result4 == jonsnow

        # scenario 5: with no @ anywhere in name, fetch username
        arya = models.User(username='arya', fullname="Arya Stark")
        self.db_session.add(arya)
        self.db_session.commit()
        result5 = models.getuser('arya')
        assert result5 == arya

        # scenario 6: with no starting with @ name and no UserEmailClaim or UserEmail
        cersei = models.User(username='cersei', fullname="Cersei Lannister")
        self.db_session.add(cersei)
        self.db_session.commit()
        result6 = models.getuser('cersei@thelannisters.co.uk')
        assert result6 is None

    def test_getextid(self):
        """Test for retrieving user given service and userid."""
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

        self.db_session.add(externalid)
        self.db_session.commit()
        result = models.getextid(service_facebook, userid=email)
        assert isinstance(result, models.UserExternalId)
        assert '<UserExternalId {service}:{username} of {user}>'.format(
            service=service_facebook, username=email, user=repr(crusoe)[1:-1]
        ) in repr(result)
