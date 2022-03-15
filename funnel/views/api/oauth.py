from __future__ import annotations

from typing import Iterable, List, Optional, cast

from flask import get_flashed_messages, jsonify, redirect, render_template, request

from baseframe import _, forms
from coaster.auth import current_auth
from coaster.sqlalchemy import failsafe_add
from coaster.utils import newsecret

from ... import app
from ...models import (
    AuthClient,
    AuthClientCredential,
    AuthCode,
    AuthToken,
    User,
    UserSession,
    db,
    getuser,
)
from ...registry import resource_registry
from ...typing import ReturnView
from ...utils import abort_null, make_redirect_url
from ..login_session import requires_client_login, requires_login_no_message
from .resource import get_userinfo


class ScopeError(Exception):
    """Requested scope is invalid or beyond access level."""


def verifyscope(scope: Iterable, auth_client: AuthClient) -> List[str]:
    """Verify if requested scope is valid for this client."""
    internal_resources = []  # Names of internal resources

    for item in scope:
        if item == '*':
            # The '*' resource (full access) is only available to trusted clients
            if not auth_client.trusted:
                raise ScopeError(_("Full access is only available to trusted clients"))
        elif item in resource_registry:
            if resource_registry[item]['trusted'] and not auth_client.trusted:
                raise ScopeError(
                    _(
                        "The resource {scope} is only available to trusted clients"
                    ).format(scope=item)
                )
            internal_resources.append(item)
        else:
            # Is this an internal wildcard resource?
            if item.endswith('/*'):
                wildcard_base = item[:-2]
                for key in resource_registry:
                    if key == wildcard_base or key.startswith(wildcard_base + '/'):
                        if (
                            resource_registry[key]['trusted']
                            and not auth_client.trusted
                        ):
                            # Skip over trusted resources if the client is not trusted
                            continue
                        internal_resources.append(key)

    internal_resources.sort()
    return internal_resources


def oauth_auth_403(reason: str) -> ReturnView:
    """Return 403 errors for /auth."""
    return render_template('oauth_403.html.jinja2', reason=reason), 403


def oauth_make_auth_code(
    auth_client: AuthClient, scope: Iterable, redirect_uri: str
) -> str:
    """
    Make an auth code for a given auth client.

    Caller must commit the database session for this to work.
    """
    authcode = AuthCode(
        user=current_auth.user,
        user_session=current_auth.session,
        auth_client=auth_client,
        scope=scope,
        redirect_uri=redirect_uri[:1024],
    )
    authcode.code = newsecret()
    db.session.add(authcode)
    return authcode.code


def clear_flashed_messages() -> None:
    """
    Clear pending flashed messages.

    This is useful when redirecting the user to a remote site where they cannot see the
    messages. If they return much later, they could be confused by a message for an
    action they do not recall.
    """
    list(get_flashed_messages())


def oauth_auth_success(
    auth_client: AuthClient,
    redirect_uri: str,
    state: str,
    code: Optional[str],
    token: Optional[AuthToken] = None,
) -> ReturnView:
    """Commit session and redirect to OAuth redirect URI."""
    clear_flashed_messages()
    db.session.commit()
    if auth_client.confidential:
        use_fragment = False
    else:
        use_fragment = True
    if token is not None:
        redirect_to = make_redirect_url(
            redirect_uri,
            use_fragment=use_fragment,
            access_token=token.token,
            token_type=token.token_type,
            expires_in=token.validity,
            scope=' '.join(token.scope),
            state=state,
        )
    else:
        redirect_to = make_redirect_url(
            redirect_uri, use_fragment=use_fragment, code=code, state=state
        )
    if use_fragment:
        return render_template(
            'oauth_public_redirect.html.jinja2',
            auth_client=auth_client,
            redirect_to=redirect_to,
        )
    response = redirect(redirect_to, code=303)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


def oauth_auth_error(
    redirect_uri: str,
    state: str,
    error: str,
    error_description: Optional[str] = None,
    error_uri: Optional[str] = None,
) -> ReturnView:
    """Return to auth client indicating that auth request resulted in an error."""
    params = {'error': error}
    if state is not None:
        params['state'] = state
    if error_description is not None:
        params['error_description'] = error_description
    if error_uri is not None:
        params['error_uri'] = error_uri
    clear_flashed_messages()
    response = redirect(
        make_redirect_url(redirect_uri, use_fragment=False, **params), code=303
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


@app.route('/api/1/auth', methods=['GET', 'POST'])
@requires_login_no_message
def oauth_authorize() -> ReturnView:
    """Provide authorization endpoint for OAuth2 server."""
    form = forms.Form()

    response_type = request.args.get('response_type')
    client_id = cast(Optional[str], request.args.get('client_id'))
    redirect_uri = cast(Optional[str], request.args.get('redirect_uri'))
    scope = cast(str, request.args.get('scope', '')).split(' ')
    state = cast(str, request.args.get('state', ''))

    # Validation 1.1: Client_id present
    if not client_id:
        return oauth_auth_403(_("Missing client_id"))

    # Validation 1.2: AuthClient exists
    credential = AuthClientCredential.get(client_id)
    if credential is not None:
        auth_client = credential.auth_client
    else:
        return oauth_auth_403(_("Unknown client_id"))

    # Validation 1.2.1: Is the client active?
    if not auth_client.active:
        return oauth_auth_error(auth_client.redirect_uri, state, 'unauthorized_client')

    # Validation 1.3: Cross-check redirect_uri
    if not redirect_uri:
        redirect_uri = auth_client.redirect_uri
        if not redirect_uri:  # Validation 1.3.1: No redirect_uri specified
            return oauth_auth_403(_("No redirect URI specified"))
    elif redirect_uri not in auth_client.redirect_uris and not auth_client.host_matches(
        redirect_uri
    ):
        return oauth_auth_error(
            auth_client.redirect_uri,
            state,
            'invalid_request',
            _("Redirect URI hostname doesn't match"),
        )

    # Validation 1.4: AuthClient allows login for this user
    if not auth_client.allow_login_for(current_auth.user):
        return oauth_auth_error(
            auth_client.redirect_uri,
            state,
            'invalid_scope',
            _("You do not have access to this application"),
        )

    # Validation 2.1: Is response_type present?
    if not response_type:
        return oauth_auth_error(
            redirect_uri, state, 'invalid_request', _("response_type missing")
        )
    # Validation 2.2: Is response_type acceptable?
    if response_type not in ['code', 'token']:
        return oauth_auth_error(redirect_uri, state, 'unsupported_response_type')

    # Validation 3.1: Is scope present?
    if not scope:
        return oauth_auth_error(
            redirect_uri, state, 'invalid_request', _("Scope not specified")
        )

    # Validation 3.2: Is scope valid?
    try:
        internal_resources = verifyscope(scope, auth_client)
    except ScopeError as scopeex:
        return oauth_auth_error(redirect_uri, state, 'invalid_scope', str(scopeex))

    # Validations complete. Now ask user for permission
    # If the client is trusted (Lastuser feature, not in OAuth2 spec), don't ask user.
    # The client does not get access to any data here -- they still have to authenticate
    # to /token.
    if request.method == 'GET' and auth_client.trusted:
        # Return auth token. No need for user confirmation
        if response_type == 'code':
            return oauth_auth_success(
                auth_client,
                redirect_uri,
                state,
                oauth_make_auth_code(auth_client, scope, redirect_uri),
            )
        return oauth_auth_success(
            auth_client,
            redirect_uri,
            state,
            code=None,
            token=oauth_make_token(
                current_auth.user, auth_client, scope, current_auth.session
            ),
        )

    # If there is an existing auth token with the same or greater scope, don't ask user
    # again; authorize silently
    existing_token = auth_client.authtoken_for(current_auth.user, current_auth.session)
    if existing_token and (
        '*' in existing_token.effective_scope
        or set(scope).issubset(set(existing_token.effective_scope))
    ):
        if response_type == 'code':
            return oauth_auth_success(
                auth_client,
                redirect_uri,
                state,
                oauth_make_auth_code(auth_client, scope, redirect_uri),
            )
        return oauth_auth_success(
            auth_client,
            redirect_uri,
            state,
            code=None,
            token=oauth_make_token(
                current_auth.user, auth_client, scope, current_auth.session
            ),
        )

    # If the user was prompted, take their input.
    if form.validate_on_submit():
        if 'accept' in request.form:
            # User said yes. Return an auth code to the client
            if response_type == 'code':
                return oauth_auth_success(
                    auth_client,
                    redirect_uri,
                    state,
                    oauth_make_auth_code(auth_client, scope, redirect_uri),
                )
            return oauth_auth_success(
                auth_client,
                redirect_uri,
                state,
                code=None,
                token=oauth_make_token(
                    current_auth.user, auth_client, scope, current_auth.session
                ),
            )
        if 'deny' in request.form:
            # User said no. Return "access_denied" error (OAuth2 spec)
            return oauth_auth_error(redirect_uri, state, 'access_denied')
        raise ValueError("Received an authorize form without a valid action")

    # GET request or POST with invalid CSRF
    return (
        render_template(
            'oauth_authorize.html.jinja2',
            form=form,
            auth_client=auth_client,
            redirect_uri=redirect_uri,
            internal_resources=internal_resources,
            resource_registry=resource_registry,
        ),
        200,
        {'X-Frame-Options': 'SAMEORIGIN'},
    )


def oauth_token_error(
    error: str, error_description: Optional[str] = None, error_uri: Optional[str] = None
) -> ReturnView:
    """Return an error status when validating an OAuth2 token request."""
    params = {'error': error}
    if error_description is not None:
        params['error_description'] = error_description
    if error_uri is not None:
        params['error_uri'] = error_uri
    response = jsonify(**params)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.status_code = 400
    return response


def oauth_make_token(
    user: Optional[User],
    auth_client: AuthClient,
    scope: Iterable,
    user_session: Optional[UserSession] = None,
) -> AuthToken:
    """Make an OAuth2 token for the given user, client, scope and optional session."""
    # Look for an existing token
    token = auth_client.authtoken_for(user, user_session)

    # If token exists, add to the existing scope
    if token is not None:
        token.add_scope(scope)
    else:
        # If there's no existing token, create one
        if auth_client.confidential:
            if user is None:
                raise ValueError("User not provided")
            token = AuthToken(  # nosec
                user=user, auth_client=auth_client, scope=scope, token_type='bearer'
            )
            token = failsafe_add(db.session, token, user=user, auth_client=auth_client)
        elif user_session is not None:
            token = AuthToken(  # nosec
                user_session=user_session,
                auth_client=auth_client,
                scope=scope,
                token_type='bearer',
            )
            token = failsafe_add(
                db.session, token, user_session=user_session, auth_client=auth_client
            )
        else:
            raise ValueError("user_session not provided")
    return token


def oauth_token_success(token: AuthToken, **params: str) -> ReturnView:
    """Return an OAuth2 token after successful validation and token generation."""
    params['access_token'] = token.token
    params['token_type'] = token.token_type
    params['scope'] = ' '.join(token.effective_scope)
    # TODO: Understand how refresh_token works.
    if token.validity:
        params['expires_in'] = token.validity
        # No refresh tokens for client_credentials tokens
        if token.user is not None:
            params['refresh_token'] = token.refresh_token
    response = jsonify(**params)
    response.headers['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    db.session.commit()
    return response


@app.route('/api/1/token', methods=['POST'])
@requires_client_login
def oauth_token() -> ReturnView:
    """Provide token endpoint for OAuth2 server."""
    # Always required parameters
    grant_type = cast(Optional[str], abort_null(request.form.get('grant_type')))
    auth_client = current_auth.auth_client  # Provided by @requires_client_login
    scope = abort_null(request.form.get('scope', '')).split(' ')
    # if grant_type == 'authorization_code' (POST)
    code = cast(Optional[str], abort_null(request.form.get('code')))
    redirect_uri = cast(Optional[str], abort_null(request.form.get('redirect_uri')))
    # if grant_type == 'password' (POST)
    username = cast(Optional[str], abort_null(request.form.get('username')))
    password = cast(Optional[str], abort_null(request.form.get('password')))
    # if grant_type == 'client_credentials'
    buid = cast(
        Optional[str],
        # XXX: Deprecated userid parameter
        abort_null(request.form.get('buid') or request.form.get('userid')),
    )

    # Validations 1: Required parameters
    if not grant_type:
        return oauth_token_error('invalid_request', _("Missing grant_type"))
    # grant_type == 'refresh_token' is not supported. All tokens are permanent unless
    # revoked
    if grant_type not in ['authorization_code', 'client_credentials', 'password']:
        return oauth_token_error('unsupported_grant_type')

    # Validations 2: client scope
    if grant_type == 'client_credentials':
        # AuthClient data; user isn't part of it OR trusted client and automatic scope
        try:
            # Confirm the client has access to the scope it wants
            verifyscope(scope, auth_client)
        except ScopeError as scopeex:
            return oauth_token_error('invalid_scope', str(scopeex))

        if buid:
            if auth_client.trusted:
                user = User.get(buid=buid)
                if user is not None:
                    # This client is trusted and can receive a user access token.
                    # However, don't grant it the scope it wants as the user's
                    # permission was not obtained. Instead, the client's
                    # pre-approved scope will be used for the token's effective scope.
                    token = oauth_make_token(
                        user=user, auth_client=auth_client, scope=[]
                    )
                    return oauth_token_success(
                        token,
                        userinfo=get_userinfo(
                            user=token.user,
                            auth_client=auth_client,
                            scope=token.effective_scope,
                        ),
                    )
                return oauth_token_error('invalid_grant', _("Unknown user"))
            return oauth_token_error('invalid_grant', _("Untrusted client app"))
        token = oauth_make_token(user=None, auth_client=auth_client, scope=scope)
        return oauth_token_success(token)

    # Validations 3: auth code
    if grant_type == 'authorization_code':
        if not code:
            return oauth_token_error('invalid_grant', _("Auth code not specified"))
        authcode = AuthCode.get_for_client(auth_client=auth_client, code=code)
        if not authcode:
            return oauth_token_error('invalid_grant', _("Unknown auth code"))
        if not authcode.is_valid():
            db.session.delete(authcode)
            db.session.commit()
            return oauth_token_error('invalid_grant', _("Expired auth code"))
        # Validations 3.1: scope in authcode
        if not scope or scope[0] == '':
            return oauth_token_error('invalid_scope', _("Scope is blank"))
        if not set(scope).issubset(set(authcode.scope)):
            return oauth_token_error('invalid_scope', _("Scope expanded"))
        # Scope not exceeded. Use whatever the authcode allows
        scope = authcode.scope
        if redirect_uri != authcode.redirect_uri:
            return oauth_token_error('invalid_client', _("redirect_uri does not match"))

        token = oauth_make_token(
            user=authcode.user, auth_client=auth_client, scope=scope
        )
        db.session.delete(authcode)
        return oauth_token_success(
            token,
            userinfo=get_userinfo(
                user=authcode.user,
                auth_client=auth_client,
                scope=token.effective_scope,
                user_session=authcode.user_session,
            ),
        )

    if grant_type == 'password':
        # Validations 4.1: password grant_type is only for trusted clients
        if not auth_client.trusted:
            # Refuse to untrusted clients
            return oauth_token_error(
                'unauthorized_client',
                _("AuthClient is not trusted for password grant_type"),
            )
        # Validations 4.2: Are username and password provided and correct?
        if not username or not password:
            return oauth_token_error(
                'invalid_request', _("Username or password not provided")
            )
        user = getuser(username)
        if user is None:
            # XXX: invalid_client doesn't seem right
            return oauth_token_error('invalid_client', _("No such user"))
        if not user.password_is(password, upgrade_hash=True):
            return oauth_token_error('invalid_client', _("Password mismatch"))
        # Validations 4.3: verify scope
        try:
            verifyscope(scope, auth_client)
        except ScopeError as scopeex:
            return oauth_token_error('invalid_scope', str(scopeex))
        # All good. Grant access
        token = oauth_make_token(user=user, auth_client=auth_client, scope=scope)
        return oauth_token_success(
            token,
            userinfo=get_userinfo(user=user, auth_client=auth_client, scope=scope),
        )
    # Execution will not reach here as grant_type is validated above
    return oauth_token_error('unsupported_grant_type')
