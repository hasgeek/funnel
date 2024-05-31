"""API views for basic resources."""

from __future__ import annotations

from collections.abc import Container
from typing import Any, Literal

from flask import abort, jsonify, render_template, request
from werkzeug.datastructures import MultiDict

from baseframe import __
from coaster.utils import getbool
from coaster.views import jsonp, requestargs, requestvalues

from ... import app
from ...auth import current_auth
from ...models import (
    Account,
    AuthClient,
    AuthClientCredential,
    AuthClientPermissions,
    AuthToken,
    LoginSession,
    Organization,
    User,
    db,
    getuser,
)
from ...registry import resource_registry
from ...typing import Response, ReturnView
from ...utils import abort_null
from ..helpers import progressive_rate_limit_validator, validate_rate_limit
from ..login_session import (
    requires_client_id_or_user_or_client_login,
    requires_client_login,
    requires_user_or_client_login,
)

ReturnResource = dict[str, Any]


def get_userinfo(
    user: Account,
    auth_client: AuthClient,
    scope: Container[str] = (),
    login_session: LoginSession | None = None,
    get_permissions: bool = True,
) -> ReturnResource:
    """Return userinfo for a given user, auth client and scope."""
    if '*' in scope or 'id' in scope or 'id/*' in scope:
        userinfo = {
            'userid': user.buid,
            'buid': user.buid,
            'uuid': user.uuid,
            'username': user.username,
            'fullname': user.fullname,
            'timezone': user.timezone,
            'avatar': user.logo_url,
            'oldids': [o.buid for o in user.oldids],
            'olduuids': [o.uuid for o in user.oldids],
        }
    else:
        userinfo = {}

    if login_session is not None:
        userinfo['sessionid'] = login_session.buid

    if '*' in scope or 'email' in scope or 'email/*' in scope:
        userinfo['email'] = str(user.email)
    if '*' in scope or 'phone' in scope or 'phone/*' in scope:
        userinfo['phone'] = str(user.phone)
    if '*' in scope or 'organizations' in scope or 'organizations/*' in scope:
        userinfo['organizations'] = {
            'owner': [
                {
                    'userid': org.buid,
                    'buid': org.buid,
                    'uuid': org.uuid,
                    'name': org.urlname,
                    'title': org.title,
                }
                for org in user.organizations_as_owner
            ],
            'admin': [
                {
                    'userid': org.buid,
                    'buid': org.buid,
                    'uuid': org.uuid,
                    'name': org.urlname,
                    'title': org.title,
                }
                for org in user.organizations_as_admin
            ],
        }

    if get_permissions:
        uperms = AuthClientPermissions.get(auth_client=auth_client, account=user)
        if uperms is not None:
            userinfo['permissions'] = uperms.access_permissions.split(' ')
    return userinfo


def resource_error(
    error: str, description: str | None = None, uri: str | None = None
) -> Response:
    """Return an error response."""
    params = {'status': 'error', 'error': error}
    if description:
        params['error_description'] = description
    if uri:
        params['error_uri'] = uri

    response = jsonify(params)
    response.headers['Cache-Control'] = (
        'private, no-cache, no-store, max-age=0, must-revalidate'
    )
    response.headers['Pragma'] = 'no-cache'
    response.status_code = 400
    return response


def api_result(
    status: Literal['ok', 'error', 200, 201],
    _jsonp: bool = False,
    **params: Any,
) -> Response:
    """Return an API result."""
    status_code = 200
    if status in (200, 201):
        status_code = status  # type: ignore[assignment]
        status = 'ok'
    elif status == 'error':
        status_code = 422
    params['status'] = status
    if _jsonp:
        response: Response = jsonp(params)  # type: ignore[assignment]
    else:
        response = jsonify(params)
    response.status_code = status_code
    response.headers['Cache-Control'] = (
        'private, no-cache, no-store, max-age=0, must-revalidate'
    )
    response.headers['Pragma'] = 'no-cache'
    return response


# MARK: Client access endpoints --------------------------------------------------------


@app.route('/api/1/token/verify', methods=['POST'])
@requires_client_login
def token_verify() -> ReturnView:
    """
    Return notice of deprecated endpoint.

    Funnel no longer manages inter-client resources. Previously:

    Client A has obtained a token from user U for access to the user's resources held
    in client B. It then presents this token to B and asks for the resource. B has not
    seen this token before, so it calls token/verify to validate it. Lastuser confirms
    the token is indeed valid for the resource being requested. However, with the
    removal of client resources, the only valid resource now is the '*' wildcard.
    """
    return api_result('error', error='deprecated')


@app.route('/api/1/user/get_by_userid', methods=['GET', 'POST'])
@requires_user_or_client_login
def user_get_by_userid() -> ReturnView:
    """Return user or organization with the given userid (Lastuser internal buid)."""
    buid = abort_null(request.values.get('userid'))
    if not buid:
        return api_result('error', error='no_userid_provided')
    user = Account.get(buid=buid, defercols=True)
    if user is not None:
        return api_result(
            'ok',
            _jsonp=True,
            type='user',
            userid=user.buid,
            buid=user.buid,
            uuid=user.uuid,
            name=user.username,
            title=user.fullname,
            label=user.pickername,
            timezone=user.timezone,
            oldids=[o.buid for o in user.oldids],
            olduuids=[o.uuid for o in user.oldids],
        )
    org = Organization.get(buid=buid, defercols=True)
    if org is not None:
        return api_result(
            'ok',
            _jsonp=True,
            type='organization',
            userid=org.buid,
            buid=org.buid,
            uuid=org.uuid,
            name=org.urlname,
            title=org.title,
            label=org.pickername,
        )
    return api_result('error', error='not_found', _jsonp=True)


@app.route('/api/1/user/get_by_userids', methods=['GET', 'POST'])
@requires_client_id_or_user_or_client_login
@requestvalues(('userid[]', abort_null))
def user_get_by_userids(userid: list[str]) -> ReturnView:
    """
    Return users and organizations with the given userids (Lastuser internal userid).

    This is identical to get_by_userid but accepts multiple userids and returns a list
    of matching users and organizations
    """
    if not userid:
        return api_result('error', error='no_userid_provided', _jsonp=True)
    # `userid` parameter is a list, not a scalar, since requestargs has `userid[]`
    users = Account.all(buids=userid)
    orgs = Organization.all(buids=userid)
    return api_result(
        'ok',
        _jsonp=True,
        results=[
            {
                'type': 'user',
                'buid': u.buid,
                'userid': u.buid,
                'uuid': u.uuid,
                'name': u.username,
                'title': u.fullname,
                'label': u.pickername,
                'timezone': u.timezone,
                'oldids': [o.buid for o in u.oldids],
                'olduuids': [o.uuid for o in u.oldids],
            }
            for u in users
        ]
        + [
            {
                'type': 'organization',
                'buid': o.buid,
                'userid': o.buid,
                'uuid': o.uuid,
                'name': o.name,
                'title': o.fullname,
                'label': o.pickername,
            }
            for o in orgs
        ],
    )


@app.route('/api/1/user/get', methods=['GET', 'POST'])
@requires_user_or_client_login
@requestvalues(('name', abort_null))
def user_get(name: str) -> ReturnView:
    """Return user with the given username or email address."""
    if not name:
        return api_result('error', error='no_name_provided')
    user = getuser(name)
    if user is not None:
        return api_result(
            'ok',
            type='user',
            userid=user.buid,
            buid=user.buid,
            uuid=user.uuid,
            name=user.username,
            title=user.fullname,
            label=user.pickername,
            timezone=user.timezone,
            oldids=[o.buid for o in user.oldids],
            olduuids=[o.uuid for o in user.oldids],
        )
    return api_result('error', error='not_found')


@app.route('/api/1/user/getusers', methods=['GET', 'POST'])
@requires_user_or_client_login
@requestvalues(('name[]', abort_null))
def user_getall(name: list[str]) -> ReturnView:
    """Return users with the given username or email address."""
    names = name
    buids = set()  # Dupe checker
    if not names:
        return api_result('error', error='no_name_provided')
    results = []
    for username in names:
        user = getuser(username)
        if user and user.buid not in buids:
            results.append(
                {
                    'type': 'user',
                    'userid': user.buid,
                    'buid': user.buid,
                    'uuid': user.uuid,
                    'name': user.username,
                    'title': user.fullname,
                    'label': user.pickername,
                    'timezone': user.timezone,
                    'oldids': [o.buid for o in user.oldids],
                    'olduuids': [o.uuid for o in user.oldids],
                }
            )
            buids.add(user.buid)
    if not results:
        return api_result('error', error='not_found')
    return api_result('ok', results=results)


@app.route('/api/1/user/autocomplete', methods=['GET', 'POST'])
@requires_client_id_or_user_or_client_login
@requestvalues(('q', abort_null))
def user_autocomplete(q: str = '') -> ReturnView:
    """
    Return users matching the search term.

    Looks up users by their name, @username, or by full email address.
    """
    if not q:
        return api_result('error', error='no_query_provided')
    # Limit length of query to Account.title limit
    q = q[: Account.__title_length__]

    # Setup rate limiter to not count progressive typing or backspacing towards
    # attempts. That is, sending 'abc' after 'ab' will not count towards limits, but
    # sending 'ac' will. When the user backspaces from 'abc' towards 'a', retain 'abc'
    # as the token until a different query such as 'ac' appears. This effectively
    # imposes a limit of 20 name lookups per half hour.

    validate_rate_limit(
        # As this endpoint accepts client_id+login_session in lieu of login cookie,
        # we may not have an authenticated user. Use the login_session's account in that
        # case
        'api_user_autocomplete',
        (
            current_auth.actor.uuid_b58
            if current_auth.actor
            else current_auth.session.account.uuid_b58
        ),
        # Limit 20 attempts
        20,
        # Per half hour (60s * 30m = 1800s)
        1800,
        # Use a token and validator to count progressive typing and backspacing as a
        # single rate-limited call
        token=q,
        validator=progressive_rate_limit_validator,
    )
    users = User.autocomplete(q)
    result = [
        {
            'userid': u.buid,
            'buid': u.buid,
            'uuid': u.uuid,
            'name': u.username,
            'title': u.fullname,
            'label': u.pickername,
        }
        for u in users
    ]
    return api_result('ok', users=result, _jsonp=True)


@app.route('/api/1/profile/autocomplete')
@requires_client_id_or_user_or_client_login
@requestvalues(('q', abort_null))
def profile_autocomplete(q: str = '') -> ReturnView:
    """Return accounts matching the search term."""
    if not q:
        return api_result('error', error='no_query_provided')

    # Limit length of query to Account.title
    q = q[: Account.__title_length__]

    # Setup rate limiter to not count progressive typing or backspacing towards
    # attempts. That is, sending 'abc' after 'ab' will not count towards limits, but
    # sending 'ac' will. When the user backspaces from 'abc' towards 'a', retain 'abc'
    # as the token until a different query such as 'ac' appears. This effectively
    # imposes a limit of 20 name lookups per half hour.

    validate_rate_limit(
        # As this endpoint accepts client_id+login_session in lieu of login cookie,
        # we may not have an authenticated user. Use the login_session's account in that
        # case
        'api_profile_autocomplete',
        (
            current_auth.actor.uuid_b58
            if current_auth.actor
            else current_auth.session.account.uuid_b58
        ),
        # Limit 20 attempts
        20,
        # Per half hour (60s * 30m = 1800s)
        1800,
        # Use a token and validator to count progressive typing and backspacing as a
        # single rate-limited call
        token=q,
        validator=progressive_rate_limit_validator,
    )
    profiles = Account.autocomplete(q)
    profile_names = [p.name for p in profiles]  # TODO: Update front-end, remove this
    profile_list = [
        {
            'uuid_b58': p.uuid_b58,
            'uuid_b64': p.uuid_b64,
            'name': p.name,
            'title': p.title,
            'label': p.pickername,
        }
        for p in profiles
    ]
    return api_result(
        'ok',
        profile=profile_names,  # TODO: Remove this
        profiles=profile_list,
    )


# MARK: Public endpoints ---------------------------------------------------------------


@app.route('/api/1/login/beacon.html')
@requestargs(('client_id', abort_null), ('login_url', abort_null))
def login_beacon_iframe(client_id: str, login_url: str) -> ReturnView:
    """Render a login beacon page suitable for use as an invisible iframe."""
    cred = AuthClientCredential.get(client_id)
    if cred is None:
        abort(404)
    auth_client = cred.auth_client
    if not auth_client.host_matches(login_url):
        abort(400)
    return (
        render_template(
            'login_beacon.html.jinja2', auth_client=auth_client, login_url=login_url
        ),
        200,
        {
            'Expires': 'Fri, 01 Jan 1990 00:00:00 GMT',
            'Cache-Control': 'private, max-age=86400',
        },
    )


@app.route('/api/1/login/beacon.json')
@requestargs(('client_id', abort_null))
def login_beacon_json(client_id: str) -> ReturnView:
    """Confirm if the auth client has a valid auth token for the current user."""
    cred = AuthClientCredential.get(client_id)
    if cred is None:
        abort(404)
    auth_client = cred.auth_client
    if current_auth.is_authenticated:
        token = auth_client.authtoken_for(current_auth.user)
    else:
        token = None
    response = jsonify({'hastoken': bool(token)})
    response.headers['Expires'] = 'Fri, 01 Jan 1990 00:00:00 GMT'
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response


# MARK: Token-based resource endpoints -------------------------------------------------


@app.route('/api/1/id')
@resource_registry.resource('id', __("Read your name and basic account data"))
def resource_id(
    authtoken: AuthToken,
    args: MultiDict,
    files: MultiDict | None = None,  # noqa: ARG001
) -> ReturnResource:
    """Return user's basic identity."""
    if 'all' in args and getbool(args['all']):
        return get_userinfo(
            authtoken.effective_user,
            authtoken.auth_client,
            scope=authtoken.effective_scope,
            get_permissions=True,
        )
    return get_userinfo(
        authtoken.effective_user,
        authtoken.auth_client,
        scope=['id'],
        get_permissions=False,
    )


@app.route('/api/1/session/verify', methods=['POST'])
@resource_registry.resource('session/verify', __("Verify user session"), scope='id')
def session_verify(
    authtoken: AuthToken,
    args: MultiDict,
    files: MultiDict | None = None,  # noqa: ARG001
) -> ReturnResource:
    """Verify a UserSession."""
    sessionid = abort_null(args['sessionid'])
    login_session = LoginSession.authenticate(buid=sessionid, silent=True)
    if login_session is not None and login_session.account == authtoken.effective_user:
        login_session.views.mark_accessed(auth_client=authtoken.auth_client)
        db.session.commit()
        return {
            'active': True,
            'sessionid': login_session.buid,
            'userid': login_session.account.buid,
            'buid': login_session.account.buid,
            'user_uuid': login_session.account.uuid,
            'sudo': login_session.has_sudo,
        }
    return {'active': False}


@app.route('/api/1/email')
@resource_registry.resource('email', __("Read your email address"))
def resource_email(
    authtoken: AuthToken,
    args: MultiDict,
    files: MultiDict | None = None,  # noqa: ARG001
) -> ReturnResource:
    """Return user's email addresses."""
    if 'all' in args and getbool(args['all']):
        return {
            'email': str(authtoken.effective_user.email),
            'all': [
                str(email)
                for email in authtoken.effective_user.emails
                if not email.private
            ],
        }
    return {'email': str(authtoken.effective_user.email)}


@app.route('/api/1/phone')
@resource_registry.resource('phone', __("Read your phone number"))
def resource_phone(
    authtoken: AuthToken,
    args: MultiDict,
    files: MultiDict | None = None,  # noqa: ARG001
) -> ReturnResource:
    """Return user's phone numbers."""
    if 'all' in args and getbool(args['all']):
        return {
            'phone': str(authtoken.effective_user.phone),
            'all': [str(phone) for phone in authtoken.effective_user.phones],
        }
    return {'phone': str(authtoken.effective_user.phone)}


@app.route('/api/1/user/externalids')
@resource_registry.resource(
    'user/externalids',
    __("Access your external account information such as Twitter and Google"),
    trusted=True,
)
def resource_login_providers(
    authtoken: AuthToken,
    args: MultiDict,
    files: MultiDict | None = None,  # noqa: ARG001
) -> ReturnResource:
    """Return user's login providers' data."""
    service: str | None = abort_null(args.get('service'))
    response = {}
    for extid in authtoken.effective_user.externalids:
        if service is None or extid.service == service:
            response[extid.service] = {
                'userid': str(extid.userid),
                'username': str(extid.username),
                'oauth_token': str(extid.oauth_token),
                'oauth_token_secret': str(extid.oauth_token_secret),
                'oauth_token_type': str(extid.oauth_token_type),
            }
    return response


@app.route('/api/1/organizations')
@resource_registry.resource(
    'organizations', __("Read the organizations you are a member of")
)
def resource_organizations(
    authtoken: AuthToken,
    args: MultiDict,  # noqa: ARG001
    files: MultiDict | None = None,  # noqa: ARG001
) -> ReturnResource:
    """Return user's organizations and teams that they are a member of."""
    return get_userinfo(
        authtoken.effective_user,
        authtoken.auth_client,
        scope=['organizations'],
        get_permissions=False,
    )


@app.route('/api/1/teams')
@resource_registry.resource('teams', __("Read the list of teams in your organizations"))
def resource_teams(
    authtoken: AuthToken,
    args: MultiDict,  # noqa: ARG001
    files: MultiDict | None = None,  # noqa: ARG001
) -> ReturnResource:
    """Return user's organizations' teams."""
    return get_userinfo(
        authtoken.effective_user,
        authtoken.auth_client,
        scope=['teams'],
        get_permissions=False,
    )
