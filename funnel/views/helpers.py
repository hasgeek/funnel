from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import unquote, urljoin, urlparse

from flask import (
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    request,
    session,
    url_for,
)
from werkzeug.urls import url_quote
import itsdangerous

from pytz import common_timezones
from pytz import timezone as pytz_timezone
from pytz import utc

from baseframe import _, cache, statsd
from coaster.auth import add_auth_attribute, current_auth, request_has_auth
from coaster.utils import utcnow
from coaster.views import get_current_url

from .. import app, funnelapp, lastuserapp
from ..models import (
    AuthClientCredential,
    User,
    UserSession,
    db,
    emailaddress_refcount_dropping,
)
from ..signals import user_login, user_registered
from ..utils import abort_null
from .jobs import forget_email

valid_timezones = set(common_timezones)


def app_url_for(
    app, endpoint, _external=True, _method='GET', _anchor=None, _scheme=None, **values
):
    """
    Equivalent of calling :func:`url_for` in another app's context. Notable differences:

    - Does not support blueprints as this repo does not use them
    - Does not defer to a :exc:`BuildError` handler. Caller is responsible for handling
    - However, defers to Flask's url_for if the provided app is also the current app
    """
    # 'app' here is the parameter, not the module-level import
    if current_app and current_app._get_current_object() is app:
        return url_for(
            endpoint,
            _external=_external,
            _method=_method,
            _anchor=_anchor,
            _scheme=_scheme,
            **values,
        )
    url_adapter = app.create_url_adapter(None)
    old_scheme = None
    if _scheme is not None:
        old_scheme = url_adapter.url_scheme
        url_adapter.url_scheme = _scheme
    try:
        result = url_adapter.build(
            endpoint, values, method=_method, force_external=_external
        )
    finally:
        if old_scheme is not None:
            url_adapter.url_scheme = old_scheme
    if _anchor:
        result += f'#{url_quote(_anchor)}'
    return result


class LoginManager(object):
    """
    Compatibility login manager that resembles Flask-Lastuser
    """

    # Flag for Baseframe to avoid attempting API calls
    is_master_data_source = True

    @property
    def autocomplete_endpoint(self):
        if current_app != app:
            return app_url_for(app, 'user_autocomplete')
        else:
            result = url_for('user_autocomplete')
        return result

    @property
    def getuser_endpoint(self):
        if current_app != app:
            return app_url_for(app, 'user_get_by_userids')
        else:
            result = url_for('user_get_by_userids')
        return result

    def _load_user(self):
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
                current_auth.session.access()

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


def localize_micro_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_timestamp(int(timestamp) / 1000, from_tz, to_tz)


def localize_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_date(datetime.fromtimestamp(int(timestamp)), from_tz, to_tz)


def localize_date(date, from_tz=utc, to_tz=utc):
    if from_tz and to_tz:
        if isinstance(from_tz, str):
            from_tz = pytz_timezone(from_tz)
        if isinstance(to_tz, str):
            to_tz = pytz_timezone(to_tz)
        if date.tzinfo is None:
            date = from_tz.localize(date)
        return date.astimezone(to_tz)
    return date


@app.template_filter('url_join')
@funnelapp.template_filter('url_join')
def url_join(base, url=''):
    return urljoin(base, url)


def mask_email(email):
    """
    Masks an email address

    >>> mask_email(u'foobar@example.com')
    u'foo***@example.com'
    >>> mask_email(u'not-email')
    u'not-em***'
    """
    if '@' not in email:
        return '{e}***'.format(e=email[:-3])
    username, domain = email.split('@')
    return '{u}***@{d}'.format(u=username[:-3], d=domain)


def clear_old_session(response):
    for cookie_name, domains in app.config.get('DELETE_COOKIES', {}).items():
        if cookie_name in request.cookies:
            for domain in domains:
                response.set_cookie(
                    cookie_name, '', expires=0, httponly=True, domain=domain
                )
    return response


app.after_request(clear_old_session)
funnelapp.after_request(clear_old_session)
lastuserapp.after_request(clear_old_session)


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def lastuser_cookie(response):
    """
    Save lastuser login cookie and hasuser JS-readable flag cookie.
    """
    if request_has_auth() and hasattr(current_auth, 'cookie'):
        if current_auth.session:
            # Don't commit if the view failed to
            db.session.rollback()
            # Update user session access timestamp...
            current_auth.session.access()
            # ...and save it
            db.session.commit()

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
        )

        response.set_cookie(
            'hasuser',
            value='1' if current_auth.is_authenticated else '0',
            max_age=31557600,  # Keep this cookie for a year.
            expires=expires,  # Expire one year from now.
            secure=current_app.config[
                'SESSION_COOKIE_SECURE'
            ],  # HTTPS cookie if session is too.
            httponly=False,
        )  # Allow reading this from JS.

    return response


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def cache_expiry_headers(response):
    if 'Expires' not in response.headers:
        response.headers['Expires'] = 'Fri, 01 Jan 1990 00:00:00 GMT'
    if 'Cache-Control' in response.headers:
        if 'private' not in response.headers['Cache-Control']:
            response.headers['Cache-Control'] = (
                'private, ' + response.headers['Cache-Control']
            )
    else:
        response.headers['Cache-Control'] = 'private'
    return response


@funnelapp.url_defaults
def add_profile_parameter(endpoint, values):
    if funnelapp.url_map.is_endpoint_expecting(endpoint, 'profile'):
        if 'profile' not in values:
            values['profile'] = g.profile.name if g.profile else None


def requires_login(f):
    """
    Decorator to require a login for the given view.
    """

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


def requires_client_login(f):
    """
    Decorator to require a client login via HTTP Basic Authorization.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        else:
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
        else:
            return result

    return decorated_function


def get_scheme_netloc(uri):
    parsed_uri = urlparse(uri)
    return (parsed_uri.scheme, parsed_uri.netloc)


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
        else:
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
    user_session.access()
    add_auth_attribute('session', user_session)
    current_auth.cookie['sessionid'] = user_session.buid
    current_auth.cookie['userid'] = user.buid
    session.permanent = True
    autoset_timezone(user)
    user_login.send(user)


def autoset_timezone(user):
    # Set the user's timezone automatically if available
    if user.timezone is None or user.timezone not in valid_timezones:
        if request.cookies.get('timezone'):
            timezone = unquote(request.cookies.get('timezone'))
            if timezone in valid_timezones:
                user.timezone = timezone


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
    )
    return response


def validate_rate_limit(
    resource, identifier, attempts, timeout, token=None, validator=None
):
    """
    Confirm the rate limit has not been reached for the given string identifier, number
    of attempts, and timeout period. Uses a simple limiter: once the number of attempts
    is reached, no further attempts can be made for timeout seconds.

    Aborts with HTTP 429 in case the limit has been reached.

    :param str identifier: Identifier for type of request and entity being rate limited
    :param int attempts: Number of attempts allowed
    :param int timeout: Duration in seconds to block after attempts are exhausted
    :param str token: For advanced use, a token to check against for future calls
    :param validator: A validator that receives the token and returns two bools
        ``(count_this, retain_previous_token)``

    For an example of how the token and validator are used, see the user_autocomplete
    endpoint in views/auth_resource.py
    """
    statsd.set('rate_limit', identifier, rate=1, tags={'resource': resource})
    cache_key = 'rate_limit/v1/%s/%s' % (resource, identifier)
    cache_value = cache.get(cache_key)
    if cache_value is None:
        count, cache_token = None, None
        statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 201})
    else:
        count, cache_token = cache_value
    if not count or not isinstance(count, int):
        count = 0
    if count >= attempts:
        statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 429})
        abort(429)
    if validator is not None:
        result, retain_token = validator(cache_token)
        if retain_token:
            token = cache_token
        if result:
            current_app.logger.debug(
                "Rate limit +1 (validated with %s, retain %r) for %s/%s",
                cache_token,
                retain_token,
                resource,
                identifier,
            )
            count += 1
            statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 200})
        else:
            current_app.logger.debug(
                "Rate limit +0 (validated with %s, retain %r) for %s/%s",
                cache_token,
                retain_token,
                resource,
                identifier,
            )
    else:
        current_app.logger.debug("Rate limit +1 for %s/%s", resource, identifier)
        count += 1
        statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 200})
    # Always set count, regardless of validator output
    current_app.logger.debug(
        "Setting rate limit usage for %s/%s to %s with token %s",
        resource,
        identifier,
        count,
        token,
    )
    cache.set(cache_key, (count, token), timeout=timeout)


# If an email address had a reference count drop during the request, make a note of
# its email_hash, and at the end of the request, queue a background job. The job will
# call .refcount() and if it still has zero references, it will be marked as forgotten
# by having the email column set to None.

# It is possible for an email address to have its refcount drop and rise again within
# the request, so it's imperative to wait until the end of the request before attempting
# to forget it. Ideally, this job should wait even longer, for several minutes or even
# up to a day.


@emailaddress_refcount_dropping.connect
def forget_email_in_request_teardown(sender):
    if g:  # Only do this if we have an app context
        if not hasattr(g, 'forget_email_hashes'):
            g.forget_email_hashes = set()
        g.forget_email_hashes.add(sender.email_hash)


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def forget_email_in_background_job(response):
    if hasattr(g, 'forget_email_hashes'):
        for email_hash in g.forget_email_hashes:
            forget_email.queue(email_hash)
    return response
