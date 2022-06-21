"""Support functions for requiring authentication and maintaining a login session."""

from __future__ import annotations

from datetime import timedelta
from functools import wraps
from typing import Optional, Type

from flask import (
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    request,
    session,
    url_for,
)
import itsdangerous

import geoip2.errors

from baseframe import _, statsd
from baseframe.forms import render_form
from coaster.auth import add_auth_attribute, current_auth, request_has_auth
from coaster.utils import utcnow
from coaster.views import get_current_url, get_next_url

from .. import app
from ..forms import OtpForm, PasswordForm
from ..models import (
    AuthClient,
    AuthClientCredential,
    User,
    UserSession,
    UserSessionExpiredError,
    UserSessionInactiveUserError,
    UserSessionRevokedError,
    auth_client_user_session,
    db,
    user_session_validity_period,
)
from ..proxies import request_wants
from ..serializers import lastuser_serializer
from ..signals import user_login, user_registered
from ..utils import abort_null
from .helpers import (
    app_url_for,
    autoset_timezone_and_locale,
    get_scheme_netloc,
    render_redirect,
    validate_rate_limit,
)
from .otp import OtpReasonError, OtpSession, OtpTimeoutError

# Constant value, needed for cookie max_age
user_session_validity_period_total_seconds = int(
    user_session_validity_period.total_seconds()
)


class LoginManager:
    """Compatibility login manager that resembles Flask-Lastuser."""

    # For compatibility with baseframe.forms.fields.UserSelectFieldBase
    usermanager: Type
    usermodel = User

    # Flag for Baseframe to avoid attempting API calls
    is_master_data_source = True

    @property
    def autocomplete_endpoint(self):
        return app_url_for(app, 'user_autocomplete')

    @property
    def getuser_endpoint(self):
        return app_url_for(app, 'user_get_by_userids')

    @staticmethod
    def _load_user():
        """Load the user object to `current_auth` if there's a buid in the session."""
        add_auth_attribute('user', None)
        add_auth_attribute('session', None)

        lastuser_cookie = {}
        _lastuser_cookie_headers = {}  # Ignored for now, intended for future changes

        # Migrate data from Flask cookie session
        if 'sessionid' in session:
            lastuser_cookie['sessionid'] = session.pop('sessionid')
        if 'userid' in session:
            lastuser_cookie['userid'] = session.pop('userid')

        if 'lastuser' in request.cookies:
            try:
                (
                    lastuser_cookie,
                    _lastuser_cookie_headers,
                ) = lastuser_serializer().loads(
                    request.cookies['lastuser'], return_header=True
                )
            except itsdangerous.BadSignature:
                lastuser_cookie = {}

        add_auth_attribute('cookie', lastuser_cookie)
        # We are dependent on `add_auth_attribute` not making a copy of the dict

        if 'sessionid' in lastuser_cookie:
            try:
                add_auth_attribute(
                    'session',
                    UserSession.authenticate(
                        buid=lastuser_cookie['sessionid'], silent=False
                    ),
                )
                if current_auth.session:
                    add_auth_attribute('user', current_auth.session.user)
                else:
                    # Invalid session. This is not supposed to happen unless there's an
                    # error that is (a) setting an invalid session id, or (b) deleting
                    # the session object instead of revoking it.
                    current_app.logger.error(
                        "Got an unknown user session %s; logging out",
                        lastuser_cookie['sessionid'],
                    )
                    logout_internal()
            except UserSessionExpiredError:
                flash(
                    _(
                        "Looks like you haven’t been here in a while."
                        " Please login again"
                    ),
                    'info',
                )
                current_app.logger.info("Got an expired user session; logging out")
                add_auth_attribute('session', None)
                logout_internal()
            except UserSessionRevokedError:
                flash(
                    _(
                        "Your login session was revoked from another device."
                        " Please login again"
                    ),
                    'info',
                )
                current_app.logger.info("Got a revoked user session; logging out")
                add_auth_attribute('session', None)
                logout_internal()
            except UserSessionInactiveUserError as exc:
                inactive_user = exc.args[0].user
                if inactive_user.state.SUSPENDED:
                    flash(_("Your account has been suspended"))
                elif inactive_user.state.DELETED:
                    flash(
                        _("This login is for a user account that is no longer present")
                    )
                else:
                    flash(_("Your account is not active"))
                current_app.logger.info("Got an inactive user; logging out")
                add_auth_attribute('session', None)
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


@UserSession.views('mark_accessed')
def session_mark_accessed(
    obj: UserSession,
    auth_client: Optional[AuthClient] = None,
    ipaddr: Optional[str] = None,
    user_agent: Optional[str] = None,
):
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
        if auth_client is not None:
            if (
                auth_client not in obj.auth_clients
            ):  # self.auth_clients is defined via AuthClient.user_sessions
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
            ipaddr = (request.remote_addr or '') if ipaddr is None else ipaddr
            # Attempt to save geonameid and ASN from IP address
            try:
                if app.geoip_city is not None and (
                    obj.geonameid_city is None or ipaddr != obj.ipaddr
                ):
                    city_lookup = app.geoip_city.city(ipaddr)
                    obj.geonameid_city = city_lookup.city.geoname_id
                    obj.geonameid_subdivision = (
                        city_lookup.subdivisions.most_specific.geoname_id
                    )
                    obj.geonameid_country = city_lookup.country.geoname_id
            except (ValueError, geoip2.errors.GeoIP2Error):
                obj.geonameid_city = None
                obj.geonameid_subdivision = None
                obj.geonameid_country = None
            try:
                if app.geoip_asn is not None and (
                    obj.geoip_asn is None or ipaddr != obj.ipaddr
                ):
                    asn_lookup = app.geoip_asn.asn(ipaddr)
                    obj.geoip_asn = asn_lookup.autonomous_system_number
            except (ValueError, geoip2.errors.GeoIP2Error):
                obj.geoip_asn = None
            # Save IP address and user agent if they've changed
            if ipaddr != obj.ipaddr:
                obj.ipaddr = ipaddr
            user_agent = (
                (str(request.user_agent.string[:250]) or '')
                if user_agent is None
                else user_agent
            )
            if user_agent != obj.user_agent:
                obj.user_agent = user_agent

    # Use integer id instead of uuid_b58 here because statsd documentation is
    # unclear on what data types a set accepts. Applies to both etsy's and telegraf.
    statsd.set('users.active_sessions', obj.id, rate=1)
    statsd.set('users.active_users', obj.user.id, rate=1)


# Also add future hasjob app here
@app.after_request
def clear_old_session(response):
    for cookie_name, domains in app.config.get('DELETE_COOKIES', {}).items():
        if cookie_name in request.cookies:
            for domain in domains:
                response.set_cookie(
                    cookie_name, '', expires=0, httponly=True, domain=domain
                )
    return response


# Also add future hasjob app here
@app.after_request
def set_lastuser_cookie(response):
    """Save lastuser login cookie and hasuser JS-readable flag cookie."""
    if request_has_auth() and hasattr(current_auth, 'cookie'):
        response.vary.add('Cookie')
        expires = utcnow() + timedelta(days=365)
        response.set_cookie(
            'lastuser',
            value=lastuser_serializer().dumps(
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
            # Using SameSite=Strict will make the browser not send this cookie when
            # the user arrives from an external site, including an OAuth2 callback. This
            # breaks the auth flow, so we must use the Lax policy
            samesite='Lax',
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
            samesite='None',
        )

    return response


# Also add future hasjob app here
@app.after_request
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


def save_session_next_url() -> bool:
    """
    Save the next URL to the session.

    In a GET request, the ``next`` request argument always takes priority over a
    previously saved next destination.
    """
    if 'next' not in session or (request.method == 'GET' and 'next' in request.args):
        session['next'] = get_next_url(referrer=True)
        return True
    return False


def requires_login(f):
    """Decorate a view to require login."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)
        if not current_auth.is_authenticated:
            flash(_("You need to be logged in for that page"), 'info')
            return redirect(url_for('login', next=get_current_url()))
        return f(*args, **kwargs)

    return decorated_function


def requires_login_no_message(f):
    """
    Decorate a view to require login, without displaying a friendly message.

    Used on views where the user is informed in advance that login is required.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)
        if not current_auth.is_authenticated:
            return redirect(url_for('login', next=get_current_url()))
        return f(*args, **kwargs)

    return decorated_function


def requires_sudo(f):
    """
    Decorate a view to require user to have re-authenticated recently.

    Requires the endpoint to support the POST method, as it renders a password form
    within the same request, avoiding redirecting the user to a gatekeeping endpoint
    unless the request needs JSON, in which case a HTML form cannot be rendered. The
    user is redirected to the `account_sudo` endpoint in this case.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)
        # If the user is not logged in, require login first
        if not current_auth.is_authenticated:
            flash(_("You need to be logged in for that page"), 'info')
            return render_redirect(url_for('login', next=get_current_url()))
        if current_auth.session.has_sudo:
            # This user authenticated recently. Nothing further required.
            return f(*args, **kwargs)

        if request_wants.json:
            # A JSON-only endpoint can't render a form, so we have to redirect
            # the browser to the account_sudo endpoint, asking it to redirect
            # back here after getting the user's password. That will be:
            # `url_for('account_sudo', next=request.url)`. Ideally, a fragment
            # identifier should be included to reload to the same dialog the
            # user was sent away from.

            return make_response(
                jsonify(
                    status='error',
                    error='requires_sudo',
                    error_description=_(
                        "This request must be confirmed with your password"
                    ),
                ),
                422,
            )

        form = None
        anchor = current_auth.user.default_anchor()

        if request.method == 'GET':
            # If the user has a password, ask for it
            if current_auth.user.pw_hash:
                form = PasswordForm(edit_user=current_auth.user)
                # A future version of this form may accept password or 2FA (U2F or TOTP)
            # User does not have a password. Try to send an OTP
            elif anchor:
                otp_session = OtpSession.make(
                    'sudo', user=current_auth.user, anchor=anchor
                )
                if otp_session.send():
                    form = OtpForm(valid_otp=otp_session.otp)
            if form is None:
                flash(
                    _(
                        "This operation requires you to confirm your password. However,"
                        " your account does not have a password, so you must set one"
                        " first"
                    ),
                    'info',
                )
                session['next'] = get_current_url()
                return render_redirect(url_for('change_password'))

        elif request.method == 'POST':
            try:
                formid = abort_null(request.form.get('form.id'))
                if formid == 'sudo-otp':
                    otp_session = OtpSession.retrieve('sudo')
                    form = OtpForm(valid_otp=otp_session.otp)
                elif formid == 'sudo-password':
                    form = PasswordForm(edit_user=current_auth.user)
                else:
                    # Unknown form
                    abort(403)
                validate_rate_limit('sudo', current_auth.user.userid, 5, 60)
                if form.validate_on_submit():
                    # User has successfully authenticated. Update their sudo timestamp
                    # and reload the page with a GET request, as the wrapped view may
                    # need to render its own form
                    current_auth.session.set_sudo()
                    db.session.commit()
                    continue_url = session.pop('next', request.url)
                    OtpSession.delete()
                    return render_redirect(continue_url, code=303)
            except OtpTimeoutError as exc:
                reason = str(exc)
                current_app.logger.info("Sudo OTP timed out with %s", reason)
                otp_session = OtpSession.make(
                    'sudo', user=current_auth.user, anchor=anchor
                )
                if not otp_session.send():
                    form = OtpForm(valid_otp=otp_session.otp)
                    abort(500)  # FIXME: Figure out likelihood and resolution
                form = OtpForm(valid_otp=otp_session.otp)
            except OtpReasonError as exc:
                reason = str(exc)
                current_app.logger.info("Sudo got OTP meant for %s", reason)
                abort(403)
        else:
            abort(405)  # Only GET and POST are supported

        if isinstance(form, OtpForm):
            title = _("Confirm this operation with an OTP")
            formid = 'sudo-otp'
        elif isinstance(form, PasswordForm):
            title = _("Confirm with your password to proceed")
            formid = 'sudo-password'
        else:
            abort(500)  # This should never happen

        if request_wants.json:
            # A JSON-only endpoint can't render a form, so we have to redirect the
            # browser to the account_sudo endpoint, asking it to redirect back here
            # after getting the user's password. That will be:
            # `url_for('account_sudo', next=request.url)`. Ideally, a fragment
            # identifier should be included to reload to the same dialog the user
            # was sent away from.

            return make_response(
                jsonify(
                    status='error',
                    error='requires_sudo',
                    error_description=_(
                        "This request must be confirmed with your password"
                    ),
                ),
                422,
            )
        if request_wants.html_fragment:
            return render_redirect(url=request.url, code=303)

        return render_form(
            form=form,
            title=title,
            formid=formid,
            submit=_("Confirm"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    return decorated_function


def requires_site_editor(f):
    """Decorate a view to require site editor permission."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        add_auth_attribute('login_required', True)
        if not current_auth.user or not current_auth.user.is_site_editor:
            abort(403)
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
    if credential is not None:
        credential.accessed_at = db.func.utcnow()
        db.session.commit()
    add_auth_attribute('auth_client', credential.auth_client, actor=True)
    return None


def requires_client_login(f):
    """Decorate a view to require a client login via HTTP Basic Authorization."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        return result

    return decorated_function


def requires_user_or_client_login(f):
    """
    Decorate a view to require a user or client login.

    User login should be via an auth cookie, client login via HTTP Basic Authentication.
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
    Decorate view to require a client_id and session, or a user, or client login.

    Looks for `client_id` and session in the request args, user in an auth cookie, or
    client via HTTP Basic Authentication.
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
    Login a user and create a session.

    If the login is from funnelapp (future hasjob), reuse the existing session.
    """
    add_auth_attribute('user', user)
    if not user_session or user_session.user != user:
        user_session = UserSession(user=user, login_service=login_service)
    user_session.views.mark_accessed()
    add_auth_attribute('session', user_session)
    current_auth.cookie['sessionid'] = user_session.buid
    current_auth.cookie['userid'] = user.buid
    session.permanent = True
    autoset_timezone_and_locale(user)
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
    session.pop('login_nonce', None)  # Used by funnelapp (future: hasjob)
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
        # Keep this cookie for a year
        max_age=user_session_validity_period_total_seconds,
        # Expire one year from now
        expires=utcnow() + user_session_validity_period,
        secure=current_app.config['SESSION_COOKIE_SECURE'],
        httponly=True,
        samesite='Lax',
    )
    return response
