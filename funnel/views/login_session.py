from datetime import timedelta
from functools import wraps

from flask import Response, current_app, flash, redirect, request, session, url_for
import itsdangerous

from baseframe import _, statsd
from coaster.auth import add_auth_attribute, current_auth, request_has_auth
from coaster.utils import utcnow
from coaster.views import get_current_url

from .. import app, funnelapp, lastuserapp
from ..models import (
    AuthClientCredential,
    User,
    UserSession,
    auth_client_user_session,
    db,
)
from ..signals import user_login, user_registered
from ..utils import abort_null
from .helpers import app_url_for, autoset_timezone, get_scheme_netloc


class LoginManager:
    """Compatibility login manager that resembles Flask-Lastuser."""

    # Flag for Baseframe to avoid attempting API calls
    is_master_data_source = True

    @property
    def autocomplete_endpoint(self):
        if current_app != app:
            return app_url_for(app, 'user_autocomplete')
        return url_for('user_autocomplete')

    @property
    def getuser_endpoint(self):
        if current_app != app:
            return app_url_for(app, 'user_get_by_userids')
        return url_for('user_get_by_userids')

    @staticmethod
    def _load_user():
        """
        If there's a buid in the session, retrieve the user object and add
        to the request namespace object g.
        """
        add_auth_attribute('user', None)
        add_auth_attribute('session', None)

        lastuser_cookie = {}
        lastuser_cookie_headers = {}  # Ignored for now, intended for future changes

        # Migrate data from Flask cookie session
        if 'sessionid' in session:
            lastuser_cookie['sessionid'] = session.pop('sessionid')
        if 'userid' in session:
            lastuser_cookie['userid'] = session.pop('userid')

        if 'lastuser' in request.cookies:
            try:
                (
                    lastuser_cookie,
                    lastuser_cookie_headers,
                ) = current_app.cookie_serializer.loads(
                    request.cookies['lastuser'], return_header=True
                )
            except itsdangerous.exc.BadSignature:
                lastuser_cookie = {}

        add_auth_attribute('cookie', lastuser_cookie)
        # We are dependent on `add_auth_attribute` not making a copy of the dict

        if 'sessionid' in lastuser_cookie:
            add_auth_attribute(
                'session', UserSession.authenticate(buid=lastuser_cookie['sessionid'])
            )
            if current_auth.session:
                add_auth_attribute('user', current_auth.session.user)
            else:
                # Invalid session. Logout the user
                current_app.logger.info("Got an invalid/expired session; logging out")
                logout_internal()

        # Transition users with 'userid' to 'sessionid'
        if not current_auth.session and 'userid' in lastuser_cookie:
            add_auth_attribute('user', User.get(buid=lastuser_cookie['userid']))
            if current_auth.is_authenticated:
                add_auth_attribute('session', UserSession(user=current_auth.user))
                current_auth.session.views.mark_accessed()

        if current_auth.session:
            lastuser_cookie['sessionid'] = current_auth.session.buid
        else:
            lastuser_cookie.pop('sessionid', None)
        if current_auth.is_authenticated:
            lastuser_cookie['userid'] = current_auth.user.buid
        else:
            lastuser_cookie.pop('userid', None)

        # Stop tracking updated_at as it's unused and the session has its own timestamp
        lastuser_cookie.pop('updated_at', None)

        # This will be set to True downstream by the requires_login decorator
        add_auth_attribute('login_required', False)


# For compatibility with baseframe.forms.fields.UserSelectFieldBase
LoginManager.usermanager = LoginManager
LoginManager.usermodel = User


@UserSession.views('mark_accessed')
def session_mark_accessed(obj, auth_client=None, ipaddr=None, user_agent=None):
    """
    Mark a session as currently active.

    :param auth_client: For API calls from clients, save the client instead of IP
        address and User-Agent
    """
    # `accessed_at` will be different from the automatic `updated_at` in one
    # crucial context: when the session was revoked from a different session.
    # `accessed_at` won't be updated at that time.
    obj.accessed_at = db.func.utcnow()
    with db.session.no_autoflush:
        if auth_client:
            if (
                auth_client not in obj.auth_clients
            ):  # self.auth_clients is defined via Client.user_sessions
                obj.auth_clients.append(auth_client)
            else:
                # If we've seen this client in this session before, only update the
                # timestamp
                db.session.execute(
                    auth_client_user_session.update()
                    .where(auth_client_user_session.c.user_session_id == obj.id)
                    .where(auth_client_user_session.c.auth_client_id == auth_client.id)
                    .values(accessed_at=db.func.utcnow())
                )
        else:
            obj.ipaddr = (request.remote_addr or '') if ipaddr is None else ipaddr
            obj.user_agent = (
                (str(request.user_agent.string[:250]) or '')
                if user_agent is None
                else user_agent
            )

    # Use integer id instead of uuid_b58 here because statsd documentation is
    # unclear on what data types a set accepts. Applies to both etsy's and telegraf.
    statsd.set('users.active_sessions', obj.id, rate=1)
    statsd.set('users.active_users', obj.user.id, rate=1)


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def clear_old_session(response):
    for cookie_name, domains in app.config.get('DELETE_COOKIES', {}).items():
        if cookie_name in request.cookies:
            for domain in domains:
                response.set_cookie(
                    cookie_name, '', expires=0, httponly=True, domain=domain
                )
    return response


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def set_lastuser_cookie(response):
    """Save lastuser login cookie and hasuser JS-readable flag cookie."""
    if request_has_auth() and hasattr(current_auth, 'cookie'):
        expires = utcnow() + timedelta(days=365)
        response.set_cookie(
            'lastuser',
            value=current_app.cookie_serializer.dumps(
                current_auth.cookie, header_fields={'v': 1}
            ),
            # Keep this cookie for a year.
            max_age=31557600,
            # Expire one year from now.
            expires=expires,
            # Place cookie in master domain.
            domain=current_app.config.get('LASTUSER_COOKIE_DOMAIN'),
            # HTTPS cookie if session is too.
            secure=current_app.config['SESSION_COOKIE_SECURE'],
            # Don't allow reading this from JS.
            httponly=True,
            # Don't allow lastuser cookie outside first-party use
            samesite='Strict',
        )

        response.set_cookie(
            'hasuser',
            value='1' if current_auth.is_authenticated else '0',
            # Keep this cookie for a year.
            max_age=31557600,
            # Expire one year from now.
            expires=expires,
            # HTTPS cookie if session is too.
            secure=current_app.config['SESSION_COOKIE_SECURE'],
            # Allow reading this from JS.
            httponly=False,
            # Allow this cookie to be read in third-party website context
            samesite='Lax',
        )

    return response


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def update_user_session_timestamp(response):
    """Mark a user session as accessed at the end of every request."""
    if request_has_auth() and current_auth.session:
        # Setup a callback to update the session after the request has returned a
        # response to the user-agent. There will be no request or app context in this
        # callback, so we create a closure containing the necessary data in local vars
        user_session = current_auth.session
        ipaddr = request.remote_addr
        user_agent = str(request.user_agent.string[:250])

        @response.call_on_close
        def mark_session_accessed_after_response():
            # App context is needed for the call to statsd in mark_accessed()
            with app.app_context():
                # 1. Add object back to the current database session as it's not
                # known here. We are NOT using session.merge as we don't need to
                # refresh data from the db. SQLAlchemy will automatically load
                # missing data should that be necessary (eg: during login)
                db.session.add(user_session)
                # 2. Update user session access timestamp
                user_session.views.mark_accessed(ipaddr=ipaddr, user_agent=user_agent)
                # 3. Commit it
                db.session.commit()

    return response


def requires_login(f):
    """Decorator to require a login for the given view."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)
        if not current_auth.is_authenticated:
            flash(_("You need to be logged in for that page"), 'info')
            session['next'] = get_current_url()
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def requires_login_no_message(f):
    """
    Decorator to require a login for the given view.
    Does not display a message asking the user to login.
    However, if a message received in ``request.args['message']``,
    it is displayed. This is an insecure channel for client apps
    to display a helper message.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)
        if not current_auth.is_authenticated:
            session['next'] = get_current_url()
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def _client_login_inner():
    if request.authorization is None or not request.authorization.username:
        return Response(
            'Client credentials required',
            401,
            {'WWW-Authenticate': 'Basic realm="Client credentials"'},
        )
    credential = AuthClientCredential.get(name=request.authorization.username)
    if credential is None or not credential.secret_is(
        request.authorization.password, upgrade_hash=True
    ):
        return Response(
            'Invalid client credentials',
            401,
            {'WWW-Authenticate': 'Basic realm="Client credentials"'},
        )
    if credential:
        credential.accessed_at = db.func.utcnow()
        db.session.commit()
    add_auth_attribute('auth_client', credential.auth_client, actor=True)
    return None


def requires_client_login(f):
    """Decorator to require a client login via HTTP Basic Authorization."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        return result

    return decorated_function


def requires_user_or_client_login(f):
    """
    Decorator to require a user or client login (user by cookie, client by HTTP Basic).
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)
        # Check for user first:
        if current_auth.is_authenticated:
            return f(*args, **kwargs)
        # If user is not logged in, check for client
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        return result

    return decorated_function


def requires_client_id_or_user_or_client_login(f):
    """
    Decorator to require a client_id and session or a user or client login
    (client_id and session in the request args, user by cookie, client by HTTP Basic).
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)

        # Is there a user? Go right ahead
        if current_auth.is_authenticated:
            return f(*args, **kwargs)

        # Check if http referrer and given client id match a registered client
        if (
            'client_id' in request.values
            and 'session' in request.values
            and request.referrer
        ):
            client_cred = AuthClientCredential.get(
                abort_null(request.values['client_id'])
            )
            if client_cred is not None and get_scheme_netloc(
                client_cred.auth_client.website
            ) == get_scheme_netloc(request.referrer):
                user_session = UserSession.authenticate(
                    buid=abort_null(request.values['session'])
                )
                if user_session is not None:
                    # Add this user session to current_auth so the wrapped function
                    # knows who it's operating for. However, this is not proper
                    # authentication, so do not tag this as an actor.
                    add_auth_attribute('session', user_session)
                    return f(*args, **kwargs)

        # If we didn't get a valid client_id and session, and the user is not logged in,
        # check for client credentials in the request authorization header.
        # If no error reported, call the function, else return error.
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        return result

    return decorated_function


def login_internal(user, user_session=None, login_service=None):
    """
    Login a user and create a session. If the login is from funnelapp, reuse the
    existing session.
    """
    add_auth_attribute('user', user)
    if not user_session or user_session.user != user:
        user_session = UserSession(user=user, login_service=login_service)
    user_session.views.mark_accessed()
    add_auth_attribute('session', user_session)
    current_auth.cookie['sessionid'] = user_session.buid
    current_auth.cookie['userid'] = user.buid
    session.permanent = True
    autoset_timezone(user)
    user_login.send(user)


def logout_internal():
    add_auth_attribute('user', None)
    if current_auth.session:
        current_auth.session.revoke()
        add_auth_attribute('session', None)
    session.pop('sessionid', None)
    session.pop('userid', None)
    session.pop('merge_userid', None)
    session.pop('merge_buid', None)
    session.pop('userid_external', None)
    session.pop('avatar_url', None)
    session.pop('login_nonce', None)  # Used by funnelapp
    current_auth.cookie.pop('sessionid', None)
    current_auth.cookie.pop('userid', None)
    session.permanent = False


def register_internal(username, fullname, password):
    user = User(username=username, fullname=fullname, password=password)
    if not username:
        user.username = None
    db.session.add(user)
    user_registered.send(user)
    return user


def set_loginmethod_cookie(response, value):
    response.set_cookie(
        'login',
        value,
        max_age=31557600,  # Keep this cookie for a year
        expires=utcnow() + timedelta(days=365),  # Expire one year from now
        secure=current_app.config['SESSION_COOKIE_SECURE'],
        httponly=True,
        samesite='Strict',
    )
    return response
