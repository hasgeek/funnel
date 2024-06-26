"""Tests for the OAuth2 API endpoints."""

from base64 import b64encode
from secrets import token_urlsafe
from urllib.parse import parse_qs, urlsplit

import pytest

from funnel import models

from ...conftest import CredProtocol, LoginFixtureProtocol, TestClient


def test_authcode_requires_login(client: TestClient) -> None:
    """The authcode endpoint requires a login."""
    rv = client.get('/api/1/auth', follow_redirects=True)
    assert rv.status_code == 200
    assert rv.metarefresh is not None
    # Auth is attempting to reload itself using meta-refresh to get a cookie
    assert urlsplit(rv.metarefresh.url).path == '/api/1/auth'
    rv = client.get(rv.metarefresh.url)
    assert rv.status_code == 303
    assert urlsplit(rv.location).path == '/login'


def test_authcode_wellformed(
    client: TestClient,
    login: LoginFixtureProtocol,
    user_rincewind: models.User,
    client_hex_credential: CredProtocol,
) -> None:
    """The authcode endpoint will raise 403 if not well formed."""
    login.as_(user_rincewind)

    # Incomplete request
    query_params: dict[str, str] = {}
    rv = client.get('/api/1/auth', query_string=query_params)
    assert rv.status_code == 403
    assert "Missing client_id" in rv.text

    # Unknown client
    query_params['client_id'] = 'unknown'
    rv = client.get('/api/1/auth', query_string=query_params)
    assert rv.status_code == 403
    assert "Unknown client_id" in rv.text

    # Missing redirect URI (error is sent to client as a query parameter)
    query_params['client_id'] = client_hex_credential.cred.name
    rv = client.get('/api/1/auth', query_string=query_params)
    assert rv.status_code == 303
    assert parse_qs(urlsplit(rv.location).query)['error'] == ['invalid_request']

    # TODO: Add redirect_uri, response_type, state, scope


@pytest.mark.dbcommit
@pytest.mark.filterwarnings("ignore:Object of type <AuthToken> not in session")
def test_auth_untrusted_confidential(
    client: TestClient,
    login: LoginFixtureProtocol,
    user_rincewind: models.User,
    client_hex: models.AuthClient,
    client_hex_credential: CredProtocol,
    csrf_token: str,
) -> None:
    """Test auth on an untrusted confidential auth client."""
    login.as_(user_rincewind)

    # MARK: Create a typical auth code request -----------------------------------------

    authcode_params = {
        'client_id': client_hex_credential.cred.name,
        'response_type': 'code',
        'state': token_urlsafe(),
        'scope': 'id',
        'redirect_uri': client_hex.redirect_uri,
    }
    rv = client.get(
        '/api/1/auth',
        query_string=authcode_params,
    )
    # We got an auth page
    assert rv.status_code == 200

    # There is no existing AuthToken for this client and user
    assert models.AuthToken.get_for(client_hex, account=user_rincewind) is None

    # Submit form with `accept` and CSRF token
    rv = client.post(
        '/api/1/auth',
        query_string=authcode_params,
        data={'accept': '', 'csrf_token': csrf_token},
    )
    assert rv.status_code == 303
    rparams = parse_qs(urlsplit(rv.location).query)
    assert rparams['state'] == [authcode_params['state']]
    code = rparams['code'][0]
    assert code is not None

    # MARK: Exchange code for a token --------------------------------------------------

    authtoken_params = {
        'grant_type': 'authorization_code',
        'code': code,
        # For verification, the scope and redirect URI must be presented again
        'scope': authcode_params['scope'],
        'redirect_uri': authcode_params['redirect_uri'],
    }

    auth_header = (
        'Basic '
        + b64encode(
            (
                client_hex_credential.cred.name + ':' + client_hex_credential.secret
            ).encode()
        ).decode()
    )
    rv = client.post(
        '/api/1/token',
        headers={'Authorization': auth_header},
        data=authtoken_params,
    )
    assert rv.status_code == 200
    data = rv.get_json()
    # Confirm we have an access token
    assert data['token_type'] == 'bearer'  # noqa: S105
    assert data['access_token'] is not None
    assert data['scope'] == authtoken_params['scope']

    authtoken = models.AuthToken.get_for(client_hex, account=user_rincewind)
    assert authtoken is not None
    assert authtoken.token == data['access_token']
    assert authtoken.token_type == data['token_type']

    # MARK: Ask for an auth code again, with the same scope ----------------------------

    authcode_params['state'] = token_urlsafe()
    rv = client.get(
        '/api/1/auth',
        query_string=authcode_params,
    )
    # This time there is no authorization page asking for user permission. We got
    # a redirect back, with the authcode
    assert rv.status_code == 303
    rparams = parse_qs(urlsplit(rv.location).query)
    assert rparams['code'][0] is not None

    # However, increasing the scope requires authorization once again
    authcode_params['state'] = token_urlsafe()
    authcode_params['scope'] = 'id email'
    rv = client.get(
        '/api/1/auth',
        query_string=authcode_params,
    )
    assert rv.status_code == 200


# TODO: Test flow for trusted auth clients, and for public (non-confidential) clients
