from datetime import timedelta

import pytest

from coaster.utils import buid, utcnow
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestAuthToken(TestDatabaseFixture):
    def test_authtoken_init(self):
        """Test for verifying creation of AuthToken instance."""
        auth_client = self.fixtures.auth_client
        crusoe = self.fixtures.crusoe
        result = models.AuthToken(
            auth_client=auth_client, user=crusoe, scope='id', validity=0
        )
        assert isinstance(result, models.AuthToken)
        assert result.user == crusoe
        assert result.auth_client == auth_client

    def test_authtoken_refresh(self):
        """Test to verify creation of new token while retaining the refresh token."""
        auth_client = self.fixtures.auth_client
        hagrid = models.User(username='hagrid', fullname='Rubeus Hagrid')
        auth_token = models.AuthToken(
            auth_client=auth_client, user=hagrid, algorithm='hmac-sha-1'
        )
        existing_token = auth_token.token
        existing_secret = auth_token.secret
        auth_token.refresh()
        assert existing_token != auth_token.token
        assert existing_secret != auth_token.secret

    def test_authtoken_is_valid(self):
        """Test for verifying if AuthToken's token is valid."""
        auth_client = self.fixtures.auth_client
        # scenario 1: when validity is unlimited (0)
        tomriddle = models.User(username='voldemort', fullname='Tom Riddle')
        scope = ['id', 'email']
        tomriddle_token = models.AuthToken(
            auth_client=auth_client, user=tomriddle, scope=scope, validity=0
        )
        assert tomriddle_token.is_valid()

        # scenario 2: when validity has not been given
        draco = models.User(username='draco', fullname='Draco Malfoy')
        draco_token = models.AuthToken(auth_client=auth_client, user=draco, scope=scope)
        with pytest.raises(TypeError):
            draco_token.is_valid()

        # scenario 3: when validity is limited
        harry = models.User(username='harry', fullname='Harry Potter')
        harry_token = models.AuthToken(
            auth_client=auth_client,
            user=harry,
            scope=scope,
            validity=3600,
            created_at=utcnow(),
        )
        assert harry_token.is_valid()

        # scenario 4: when validity is limited *and* the token has expired
        cedric = models.User(username='cedric', fullname='Cedric Diggory')
        cedric_token = models.AuthToken(
            auth_client=auth_client,
            user=cedric,
            scope=scope,
            validity=1,
            created_at=utcnow() - timedelta(1),
        )
        assert not cedric_token.is_valid()

    def test_authtoken_get(self):
        """Test for retreiving a AuthToken instance given a token."""
        specialdachs = self.fixtures.specialdachs
        oakley = self.fixtures.oakley
        scope = ['id']
        dachsadv = models.AuthClient(
            title="Dachshund Adventures",
            organization=specialdachs,
            confidential=True,
            website="http://dachsadv.com",
        )
        auth_token = models.AuthToken(auth_client=dachsadv, user=oakley, scope=scope)
        token = auth_token.token
        self.db_session.add(dachsadv, auth_token)
        result = models.AuthToken.get(token)
        assert isinstance(result, models.AuthToken)
        assert result.auth_client == dachsadv

    def test_authtoken_all(self):
        """Test for retreiving all AuthToken instances for given users."""
        auth_client = self.fixtures.auth_client

        # scenario 1: When users passed are an instance of Query class
        hermione = models.User(username='herminone', fullname='Hermione Granger')
        herminone_token = models.AuthToken(
            auth_client=auth_client, user=hermione, scope=['id']
        )
        myrtle = models.User(username='myrtle', fullname='Moaning Myrtle')
        myrtle_token = models.AuthToken(
            auth_client=auth_client, user=myrtle, scope=['id']
        )
        alastor = models.User(username='alastor', fullname='Alastor Moody')
        alastor_token = models.AuthToken(
            auth_client=auth_client, user=alastor, scope=['id']
        )
        greyback = models.User(username='greyback', fullname='Fenrir Greyback')
        greyback_token = models.AuthToken(
            auth_client=auth_client, user=greyback, scope=['id']
        )
        pottermania = models.Organization(
            name='pottermania', title='Pottermania', owner=hermione
        )
        self.db_session.add_all(
            [
                myrtle,
                myrtle_token,
                hermione,
                herminone_token,
                alastor,
                alastor_token,
                greyback,
                greyback_token,
                pottermania,
            ]
        )
        self.db_session.commit()

        # scenario 1
        result1 = models.AuthToken.all(pottermania.owner_users)
        assert result1 == [herminone_token]

        # Scenario 2: When users passed are not an instance of Query class
        lily = models.User(username='lily', fullname='Lily Evans Potter')
        cho = models.User(username='cho', fullname='Cho Chang')
        lily_token = models.AuthToken(
            auth_client=auth_client, user=lily, scope=['memories']
        )
        cho_token = models.AuthToken(
            auth_client=auth_client, user=cho, scope=['charms']
        )
        self.db_session.add_all([lily, lily_token, cho, cho_token])
        self.db_session.commit()

        # scenario 2 and count == 1
        result3 = models.AuthToken.all([lily])
        assert result3 == [lily_token]

        # scenario 2 and count > 1
        result4 = models.AuthToken.all([lily, cho])
        assert set(result4) == {lily_token, cho_token}

        # scenario 5: When user instances passed don't have any AuthToken against them
        oakley = self.fixtures.oakley
        piglet = self.fixtures.piglet
        users = [piglet, oakley]
        result5 = models.AuthToken.all(users)
        assert result5 == []

    def test_authtoken_user(self):
        """Test for checking AuthToken's user property."""
        crusoe = self.fixtures.crusoe
        auth_client = self.fixtures.auth_client

        user_session = models.UserSession(
            buid=buid(), user=crusoe, ipaddr='', user_agent='', accessed_at=utcnow()
        )
        auth_token_with_user_session = models.AuthToken(
            auth_client=auth_client, user=crusoe, user_session=user_session
        )
        assert isinstance(auth_token_with_user_session.user_session.user, models.User)
        assert auth_token_with_user_session.user_session.user == crusoe

        auth_token_without_user_session = models.AuthToken(
            auth_client=auth_client, user=crusoe
        )
        assert isinstance(auth_token_without_user_session._user, models.User)
        assert auth_token_without_user_session._user == crusoe

    def test_authtoken_migrate_user(self):
        """Test for migrating user who has an AuthToken issued."""
        piglet = self.fixtures.piglet
        specialdachs = self.fixtures.specialdachs
        scope_piglet = ['id', 'email']
        londontales = models.AuthClient(
            title='London tales',
            organization=specialdachs,
            confidential=True,
            website='http://londondachtales.uk',
        )
        auth_token = models.AuthToken(
            auth_client=londontales, user=piglet, scope=scope_piglet, validity=0
        )
        token = auth_token.token

        self.db_session.add(auth_token)
        self.db_session.add(londontales)
        piggles = models.User(username="piggles")
        naughtymonkey = models.User(username="naughtymonkey")
        self.db_session.add(piggles)
        self.db_session.add(naughtymonkey)
        self.db_session.commit()

        # Scenario: When only one user has authtokens associated with them
        models.AuthToken.migrate_user(piglet, naughtymonkey)
        scope_received_piglet = models.AuthToken.get(token).scope
        self.assertCountEqual(scope_received_piglet, tuple(scope_piglet))

        # Scenario: There's a existing token for newuser with the same client,
        # then we expect to: newtoken to have extended scope
        scope_piggles = ['teams']
        another_auth_token = models.AuthToken(
            auth_client=londontales, user=piggles, scope=scope_piggles
        )
        self.db_session.add(another_auth_token)
        self.db_session.commit()
        models.AuthToken.migrate_user(piglet, piggles)
        scope_received = models.AuthToken.get(another_auth_token.token).scope
        scope_expected = tuple(set(scope_piglet + scope_piggles))
        self.assertCountEqual(scope_received, scope_expected)

    def test_authtoken_algorithm(self):
        """Test for checking AuthToken's algorithm property."""
        auth_client = self.fixtures.auth_client
        snape = models.User(username='snape', fullname='Professor Severus Snape')
        valid_algorithm = 'hmac-sha-1'
        auth_token = models.AuthToken(auth_client=auth_client, user=snape)
        auth_token.algorithm = None
        assert auth_token._algorithm is None
        auth_token.algorithm = valid_algorithm
        assert auth_token._algorithm == valid_algorithm
        assert auth_token.algorithm == valid_algorithm
        with pytest.raises(ValueError):
            auth_token.algorithm = "hmac-sha-2016"
