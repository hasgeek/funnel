from sqlalchemy.exc import IntegrityError

import pytest

from funnel import db
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestScopeMixin(TestDatabaseFixture):
    def test_scopemixin_scope(self):
        """Retrieve scope on an ScopeMixin inherited class instance via `scope`."""
        scope = 'tricks'
        ginny = models.User(username='ginny', fullname='Ginny Weasley')
        auth_client = self.fixtures.auth_client
        ginny_token = models.AuthToken(
            auth_client=auth_client, user=ginny, scope=scope, validity=0
        )
        db.session.add_all([ginny, ginny_token])
        db.session.commit()
        assert ginny_token.scope == (scope,)

    def test_scopemixin_add_scope(self):
        """Test for adding scope to a ScopeMixin inherited class instance."""
        scope1 = 'spells'
        scope2 = 'charms'
        neville = models.User(username='neville', fullname='Neville Longbottom')
        auth_client = self.fixtures.auth_client
        neville_token = models.AuthToken(
            auth_client=auth_client, user=neville, validity=0, scope=scope1
        )
        db.session.add_all([neville, neville_token])
        neville_token.add_scope(scope2)
        assert neville_token.scope == (scope2, scope1)

    def test_authcode_scope_null(self):
        """`AuthCode` can't have empty scope."""
        # Scope can't be None or empty
        with pytest.raises(ValueError):
            models.AuthCode(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
                redirect_uri='http://localhost/',
                scope=None,
            )
        with pytest.raises(ValueError):
            models.AuthCode(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
                redirect_uri='http://localhost/',
                scope='',
            )
        with pytest.raises(ValueError):
            models.AuthCode(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
                redirect_uri='http://localhost/',
                scope=[],
            )
        # Committing with default None causes IntegrityError
        db.session.add(
            models.AuthCode(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
                redirect_uri='http://localhost/',
            )
        )
        # Raise IntegrityError on scope=None
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_authtoken_scope_null(self):
        """`AuthToken` can't have empty scope."""
        # Scope can't be None or empty
        with pytest.raises(ValueError):
            models.AuthToken(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
                scope=None,
            )
        with pytest.raises(ValueError):
            models.AuthToken(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
                scope='',
            )
        with pytest.raises(ValueError):
            models.AuthToken(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
                scope=[],
            )
        # Committing with default None causes IntegrityError
        db.session.add(
            models.AuthToken(
                auth_client=self.fixtures.auth_client,
                user=self.fixtures.crusoe,
            )
        )
        # Raise IntegrityError on scope=None
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_authclient_scope_null(self):
        """`AuthClient` can have empty scope."""
        auth_client = models.AuthClient(
            user=self.fixtures.crusoe,
            title="Test client",
            confidential=True,
            website='http://localhost',
            scope=None,
        )
        db.session.add(auth_client)
        db.session.commit()
        assert auth_client.scope == ()
        # Scope can be assigned a string value, but will return as a tuple
        auth_client.scope = 'test'
        assert auth_client.scope == ('test',)
        # Whitespace separators in strings will be parsed as distinct scope tokens
        auth_client.scope = 'test scope'
        # ...and will always be sorted
        assert auth_client.scope == ('scope', 'test')
        assert auth_client._scope == 'scope test'
        auth_client.scope = 'also\tscope'
        assert auth_client.scope == ('also', 'scope')
        assert auth_client._scope == 'also scope'
        # Any kind of iterable is okay
        auth_client.scope = ['another', 'scope']
        assert auth_client.scope == ('another', 'scope')
        assert auth_client._scope == 'another scope'
        # Scope can be reset to None in models that allow it (only AuthClient)
        auth_client.scope = None
        assert auth_client.scope == ()
        assert auth_client._scope is None
        auth_client.scope = ''
        assert auth_client.scope == ()
        assert auth_client._scope is None
        auth_client.scope = ()
        assert auth_client.scope == ()
        assert auth_client._scope is None


# Test scopes as a list in all ScopeMixin subclasses
# authcode, authtoken, authclient, null allowed
