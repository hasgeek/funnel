from flask import abort, jsonify, render_template, request

from baseframe import __
from coaster.auth import current_auth
from coaster.utils import getbool
from coaster.views import jsonp, requestargs

from .. import app, lastuserapp
from ..models import (
    AuthClientCredential,
    AuthClientTeamPermissions,
    AuthClientUserPermissions,
    AuthToken,
    Organization,
    User,
    UserSession,
    db,
    getuser,
)
from ..registry import resource_registry
from ..utils import abort_null
from .helpers import validate_rate_limit
from .login_session import (
    requires_client_id_or_user_or_client_login,
    requires_client_login,
    requires_user_or_client_login,
)


def get_userinfo(user, auth_client, scope=[], user_session=None, get_permissions=True):

    if '*' in scope or 'id' in scope or 'id/*' in scope:
        userinfo = {
            'userid': user.buid,
            'buid': user.buid,
            'uuid': user.uuid,
            'username': user.username,
            'fullname': user.fullname,
            'timezone': user.timezone,
            'avatar': user.avatar,
            'oldids': [o.buid for o in user.oldids],
            'olduuids': [o.uuid for o in user.oldids],
        }
    else:
        userinfo = {}

    if user_session:
        userinfo['sessionid'] = user_session.buid

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
                    'name': org.name,
                    'title': org.title,
                }
                for org in user.organizations_as_owner
            ],
            'admin': [
                {
                    'userid': org.buid,
                    'buid': org.buid,
                    'uuid': org.uuid,
                    'name': org.name,
                    'title': org.title,
                }
                for org in user.organizations_as_admin
            ],
        }

    if get_permissions:
        if auth_client.user:
            perms = AuthClientUserPermissions.get(auth_client=auth_client, user=user)
            if perms:
                userinfo['permissions'] = perms.access_permissions.split(' ')
        else:
            permsset = set()
            if user.teams:
                perms = AuthClientTeamPermissions.all_for(
                    auth_client=auth_client, user=user
                ).all()
                for permob in perms:
                    permsset.update(permob.access_permissions.split(' '))
            userinfo['permissions'] = sorted(permsset)
    return userinfo


def resource_error(error, description=None, uri=None):
    params = {'status': 'error', 'error': error}
    if description:
        params['error_description'] = description
    if uri:
        params['error_uri'] = uri

    response = jsonify(params)
    response.headers[
        'Cache-Control'
    ] = 'private, no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.status_code = 400
    return response


def api_result(status, _jsonp=False, **params):
    status_code = 200
    if status in (200, 201):
        status_code = status
        status = 'ok'
    params['status'] = status
    if _jsonp:
        response = jsonp(params)
    else:
        response = jsonify(params)
    response.status_code = status_code
    response.headers[
        'Cache-Control'
    ] = 'private, no-cache, no-store, max-age=0, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


# --- Client access endpoints -------------------------------------------------

# Client A has obtained a token from user U for access to the user's resources held
# in client B. It then presents this token to B and asks for the resource. B has not
# seen this token before, so it calls token/verify to validate it. Lastuser confirms
# the token is indeed valid for the resource being requested. However, with the
# removal of client resources, the only valid resource now is the '*' wildcard.
@app.route('/api/1/token/verify', methods=['POST'])
@lastuserapp.route('/api/1/token/verify', methods=['POST'])
@requires_client_login
def token_verify():
    token = abort_null(request.form.get('access_token'))
    client_resource = abort_null(
        request.form.get('resource')
    )  # Can only be a single resource
    if not client_resource:
        # No resource specified by caller
        return resource_error('no_resource')
    if client_resource != '*':
        # Client resources are no longer supported; only the '*' resource is
        return resource_error('unknown_resource')
    if not token:
        # No token specified by caller
        return resource_error('no_token')

    if not current_auth.auth_client.namespace:
        # This client has not defined any resources
        return api_result('error', error='client_no_resources')

    authtoken = AuthToken.get(token=token)
    if not authtoken:
        # No such auth token
        return api_result('error', error='no_token')
    if (
        current_auth.auth_client.namespace + ':' + client_resource
        not in authtoken.effective_scope
    ) and (current_auth.auth_client.namespace + ':*' not in authtoken.effective_scope):
        # Token does not grant access to this resource
        return api_result('error', error='access_denied')

    # All validations passed. Token is valid for this client and scope. Return with information on the token
    # TODO: Don't return validity. Set the HTTP cache headers instead.
    params = {
        'validity': 120
    }  # Period (in seconds) for which this assertion may be cached.
    if authtoken.user:
        params['userinfo'] = get_userinfo(
            authtoken.user, current_auth.auth_client, scope=authtoken.effective_scope
        )
    params['clientinfo'] = {
        'title': authtoken.auth_client.title,
        'userid': authtoken.auth_client.owner.buid,
        'buid': authtoken.auth_client.owner.buid,
        'uuid': authtoken.auth_client.owner.uuid,
        'owner_title': authtoken.auth_client.owner.pickername,
        'website': authtoken.auth_client.website,
        'key': authtoken.auth_client.buid,
        'trusted': authtoken.auth_client.trusted,
    }
    return api_result('ok', **params)


@app.route('/api/1/token/get_scope', methods=['POST'])
@lastuserapp.route('/api/1/token/get_scope', methods=['POST'])
@requires_client_login
def token_get_scope():
    token = abort_null(request.form.get('access_token'))
    if not token:
        # No token specified by caller
        return resource_error('no_token')

    if not current_auth.auth_client.namespace:
        # This client has not defined any resources
        return api_result('error', error='client_no_resources')

    authtoken = AuthToken.get(token=token)
    if not authtoken:
        # No such auth token
        return api_result('error', error='no_token')

    client_resources = []
    nsprefix = current_auth.auth_client.namespace + ':'
    for item in authtoken.effective_scope:
        if item.startswith(nsprefix):
            client_resources.append(item[len(nsprefix) :])

    if not client_resources:
        return api_result('error', error='no_access')

    # All validations passed. Token is valid for this client. Return with information on the token
    # TODO: Don't return validity. Set the HTTP cache headers instead.
    params = {
        'validity': 120
    }  # Period (in seconds) for which this assertion may be cached.
    if authtoken.user:
        params['userinfo'] = get_userinfo(
            authtoken.user, current_auth.auth_client, scope=authtoken.effective_scope
        )
    params['clientinfo'] = {
        'title': authtoken.auth_client.title,
        'userid': authtoken.auth_client.owner.buid,
        'buid': authtoken.auth_client.owner.buid,
        'uuid': authtoken.auth_client.owner.uuid,
        'owner_title': authtoken.auth_client.owner.pickername,
        'website': authtoken.auth_client.website,
        'key': authtoken.auth_client.buid,
        'trusted': authtoken.auth_client.trusted,
        'scope': client_resources,
    }
    return api_result('ok', **params)


@app.route('/api/1/user/get_by_userid', methods=['GET', 'POST'])
@lastuserapp.route('/api/1/user/get_by_userid', methods=['GET', 'POST'])
@requires_user_or_client_login
def user_get_by_userid():
    """
    Returns user or organization with the given userid (Lastuser internal buid)
    """
    buid = abort_null(request.values.get('userid'))
    if not buid:
        return api_result('error', error='no_userid_provided')
    user = User.get(buid=buid, defercols=True)
    if user:
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
    else:
        org = Organization.get(buid=buid, defercols=True)
        if org:
            return api_result(
                'ok',
                _jsonp=True,
                type='organization',
                userid=org.buid,
                buid=org.buid,
                uuid=org.uuid,
                name=org.name,
                title=org.title,
                label=org.pickername,
            )
    return api_result('error', error='not_found', _jsonp=True)


@app.route('/api/1/user/get_by_userids', methods=['GET', 'POST'])
@lastuserapp.route('/api/1/user/get_by_userids', methods=['GET', 'POST'])
@requires_client_id_or_user_or_client_login
@requestargs(('userid[]', abort_null))
def user_get_by_userids(userid):
    """
    Returns users and organizations with the given userids (Lastuser internal userid).
    This is identical to get_by_userid but accepts multiple userids and returns a list
    of matching users and organizations
    """
    if not userid:
        return api_result('error', error='no_userid_provided', _jsonp=True)
    users = User.all(buids=userid)
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
@lastuserapp.route('/api/1/user/get', methods=['GET', 'POST'])
@requires_user_or_client_login
@requestargs(('name', abort_null))
def user_get(name):
    """
    Returns user with the given username, email address or Twitter id
    """
    if not name:
        return api_result('error', error='no_name_provided')
    user = getuser(name)
    if user:
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
    else:
        return api_result('error', error='not_found')


@app.route('/api/1/user/getusers', methods=['GET', 'POST'])
@lastuserapp.route('/api/1/user/getusers', methods=['GET', 'POST'])
@requires_user_or_client_login
@requestargs(('name[]', abort_null))
def user_getall(name):
    """
    Returns users with the given username, email address or Twitter id
    """
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
    else:
        return api_result('ok', results=results)


@app.route('/api/1/user/autocomplete', methods=['GET', 'POST'])
@lastuserapp.route('/api/1/user/autocomplete', methods=['GET', 'POST'])
@requires_client_id_or_user_or_client_login
def user_autocomplete():
    """
    Returns users (buid, username, fullname, twitter, github or email) matching the search term.
    """
    q = abort_null(request.values.get('q', ''))
    if not q:
        return api_result('error', error='no_query_provided')
    # Limit length of query to User.fullname limit
    q = q[: User.__title_length__]

    # Setup rate limiter to not count progressive typing or backspacing towards
    # attempts. That is, sending 'abc' after 'ab' will not count towards limits, but
    # sending 'ac' will. When the user backspaces from 'abc' towards 'a', retain 'abc'
    # as the token until a different query such as 'ac' appears. This effectively
    # imposes a limit of 20 name lookups per half hour.

    validate_rate_limit(
        # As this endpoint accepts client_id+user_session in lieu of login cookie,
        # we may not have an authenticatd user. Use the user_session's user in that case
        'user_autocomplete',
        current_auth.actor.uuid_b58
        if current_auth.actor
        else current_auth.session.user.uuid_b58,
        # Limit 20 attempts
        20,
        # Per half hour (60s * 30m = 1800s)
        1800,
        # Save the query as a token. Validator will receive the previous call's token
        token=q,
        # Validator has to return two flags: (count_this, retain_previous_token)
        # prev_q will be None on the first call to the validator
        validator=lambda prev_q: (True, False)
        if not prev_q
        else (False, False)
        if q.startswith(prev_q or '')  # Progressive typing, use new query as token
        else (False, True)
        if (prev_q or '').startswith(q)  # Backspacing, keep prev longer q as token
        else (True, False),
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


# --- Public endpoints --------------------------------------------------------


@app.route('/api/1/login/beacon.html')
@lastuserapp.route('/api/1/login/beacon.html')
@requestargs(('client_id', abort_null), ('login_url', abort_null))
def login_beacon_iframe(client_id, login_url):
    cred = AuthClientCredential.get(client_id)
    auth_client = cred.auth_client if cred else None
    if auth_client is None:
        abort(404)
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
@lastuserapp.route('/api/1/login/beacon.json')
@requestargs(('client_id', abort_null))
def login_beacon_json(client_id):
    cred = AuthClientCredential.get(client_id)
    auth_client = cred.auth_client if cred else None
    if auth_client is None:
        abort(404)
    if current_auth.is_authenticated:
        token = auth_client.authtoken_for(current_auth.user)
    else:
        token = None
    response = jsonify({'hastoken': True if token else False})
    response.headers['Expires'] = 'Fri, 01 Jan 1990 00:00:00 GMT'
    response.headers['Cache-Control'] = 'private, max-age=300'
    return response


# --- Token-based resource endpoints ------------------------------------------


@app.route('/api/1/id')
@lastuserapp.route('/api/1/id')
@resource_registry.resource('id', __("Read your name and basic profile data"))
def resource_id(authtoken, args, files=None):
    """
    Return user's id
    """
    if 'all' in args and getbool(args['all']):
        return get_userinfo(
            authtoken.user,
            authtoken.auth_client,
            scope=authtoken.effective_scope,
            get_permissions=True,
        )
    else:
        return get_userinfo(
            authtoken.user, authtoken.auth_client, scope=['id'], get_permissions=False
        )


@app.route('/api/1/session/verify', methods=['POST'])
@lastuserapp.route('/api/1/session/verify', methods=['POST'])
@resource_registry.resource('session/verify', __("Verify user session"), scope='id')
def session_verify(authtoken, args, files=None):
    sessionid = abort_null(args['sessionid'])
    session = UserSession.authenticate(buid=sessionid, silent=True)
    if session and session.user == authtoken.user:
        session.views.mark_accessed(auth_client=authtoken.auth_client)
        db.session.commit()
        return {
            'active': True,
            'sessionid': session.buid,
            'userid': session.user.buid,
            'buid': session.user.buid,
            'user_uuid': session.user.uuid,
            'sudo': session.has_sudo,
        }
    else:
        return {'active': False}


@app.route('/api/1/email')
@lastuserapp.route('/api/1/email')
@resource_registry.resource('email', __("Read your email address"))
def resource_email(authtoken, args, files=None):
    """
    Return user's email addresses.
    """
    if 'all' in args and getbool(args['all']):
        return {
            'email': str(authtoken.user.email),
            'all': [str(email) for email in authtoken.user.emails if not email.private],
        }
    else:
        return {'email': str(authtoken.user.email)}


@app.route('/api/1/phone')
@lastuserapp.route('/api/1/phone')
@resource_registry.resource('phone', __("Read your phone number"))
def resource_phone(authtoken, args, files=None):
    """
    Return user's phone numbers.
    """
    if 'all' in args and getbool(args['all']):
        return {
            'phone': str(authtoken.user.phone),
            'all': [str(phone) for phone in authtoken.user.phones],
        }
    else:
        return {'phone': str(authtoken.user.phone)}


@app.route('/api/1/user/externalids')
@lastuserapp.route('/api/1/user/externalids')
@resource_registry.resource(
    'user/externalids',
    __("Access your external account information such as Twitter and Google"),
    trusted=True,
)
def resource_login_providers(authtoken, args, files=None):
    """
    Return user's login providers' data.
    """
    service = abort_null(args.get('service'))
    response = {}
    for extid in authtoken.user.externalids:
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
@lastuserapp.route('/api/1/organizations')
@resource_registry.resource(
    'organizations', __("Read the organizations you are a member of")
)
def resource_organizations(authtoken, args, files=None):
    """
    Return user's organizations and teams that they are a member of.
    """
    return get_userinfo(
        authtoken.user,
        authtoken.auth_client,
        scope=['organizations'],
        get_permissions=False,
    )


@app.route('/api/1/teams')
@lastuserapp.route('/api/1/teams')
@resource_registry.resource('teams', __("Read the list of teams in your organizations"))
def resource_teams(authtoken, args, files=None):
    """
    Return user's organizations' teams.
    """
    return get_userinfo(
        authtoken.user, authtoken.auth_client, scope=['teams'], get_permissions=False
    )
