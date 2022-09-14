"""Tests for the ScopeMixin model mixin."""
# pylint: disable=protected-access

from sqlalchemy.exc import IntegrityError

import pytest

from funnel import models


def test_scopemixin_scope(db_session, client_hex, user_rincewind) -> None:
    """Retrieve scope on an ScopeMixin inherited class instance via `scope`."""
    scope = 'tricks'
    token = models.AuthToken(
        auth_client=client_hex, user=user_rincewind, scope=scope, validity=0
    )
    db_session.add(token)
    db_session.commit()
    assert token.scope == (scope,)


def test_scopemixin_add_scope(db_session, client_hex, user_rincewind) -> None:
    """Test for adding scope to a ScopeMixin inherited class instance."""
    scope1 = 'spells'
    scope2 = 'charms'
    token = models.AuthToken(
        auth_client=client_hex, user=user_rincewind, validity=0, scope=scope1
    )
    db_session.add(token)
    token.add_scope(scope2)
    assert token.scope == (scope2, scope1)


def test_authcode_scope_null(db_session, client_hex, user_rincewind) -> None:
    """`AuthCode` can't have null scope but can have empty scope."""
    # Scope can't be None or empty
    with pytest.raises(ValueError, match='Scope cannot be None'):
        models.AuthCode(
            auth_client=client_hex,
            user=user_rincewind,
            redirect_uri='http://localhost/',
            scope=None,
        )
    # Empty scope is fine
    auth_code = models.AuthCode(
        auth_client=client_hex,
        user=user_rincewind,
        redirect_uri='http://localhost/',
        scope='',
    )
    assert auth_code.scope == ()
    assert auth_code._scope == ''
    auth_code = models.AuthCode(
        auth_client=client_hex,
        user=user_rincewind,
        redirect_uri='http://localhost/',
        scope=[],
    )
    assert auth_code.scope == ()
    assert auth_code._scope == ''
    # Committing with default None causes IntegrityError
    db_session.add(
        models.AuthCode(
            auth_client=client_hex,
            user=user_rincewind,
            redirect_uri='http://localhost/',
        )
    )
    # Raise IntegrityError on scope=None
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_authtoken_scope_null(db_session, client_hex, user_rincewind) -> None:
    """`AuthToken` can't have null scope but can have empty scope."""
    # Scope can't be None or empty
    with pytest.raises(ValueError, match='Scope cannot be None'):
        models.AuthToken(
            auth_client=client_hex,
            user=user_rincewind,
            scope=None,
        )
    # Empty scope is fine
    auth_token = models.AuthToken(
        auth_client=client_hex,
        user=user_rincewind,
        scope='',
    )
    assert auth_token.scope == ()
    assert auth_token._scope == ''
    auth_token = models.AuthToken(
        auth_client=client_hex,
        user=user_rincewind,
        scope=[],
    )
    assert auth_token.scope == ()
    assert auth_token._scope == ''
    # Committing with default None causes IntegrityError
    db_session.add(
        models.AuthToken(
            auth_client=client_hex,
            user=user_rincewind,
        )
    )
    # Raise IntegrityError on scope=None
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_authclient_scope_null(db_session, user_rincewind) -> None:
    """`AuthClient` can have empty scope."""
    auth_client = models.AuthClient(
        user=user_rincewind,
        title="Test client",
        confidential=True,
        website='http://localhost',
        scope=None,
    )
    db_session.add(auth_client)
    # db_session.commit()
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
