"""Support functions for requiring authentication and maintaining a login session."""

from __future__ import annotations

from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Optional, Type, cast

from flask import (
    Response,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    make_response,
    redirect,
    request,
    session,
    url_for,
)
import itsdangerous

from furl import furl
import geoip2.errors

from baseframe import _, statsd
from baseframe.forms import render_form
from coaster.auth import add_auth_attribute, current_auth, request_has_auth
from coaster.utils import utcnow
from coaster.views import get_current_url, get_next_url

from .. import app
from ..forms import OtpForm, PasswordForm
from ..models import (
    USER_SESSION_VALIDITY_PERIOD,
    AuthClient,
    AuthClientCredential,
    Profile,
    User,
    UserSession,
    UserSessionExpiredError,
    UserSessionInactiveUserError,
    UserSessionRevokedError,
    auth_client_user_session,
    db,
)
from ..proxies import request_wants
from ..serializers import lastuser_serializer
from ..signals import user_login, user_registered
from ..typing import ResponseType, ReturnDecorator, WrappedFunc
from ..utils import abort_null
from .helpers import (
    app_context,
    app_url_for,
    autoset_timezone_and_locale,
    get_scheme_netloc,
    metarefresh_redirect,
    render_redirect,
    session_timeouts,
    validate_rate_limit,
)
from .otp import OtpSession, OtpTimeoutError

# --- Constants ------------------------------------------------------------------------

#: User session validity in seconds, needed for cookie max_age
USER_SESSION_VALIDITY_PERIOD_TOTAL_SECONDS = int(
    USER_SESSION_VALIDITY_PERIOD.total_seconds()
)
#: For quick lookup of matching supported methods in request.url_rule.methods
GET_AND_POST = frozenset({'GET', 'POST'})
#: Form id for sudo OTP form
FORMID_SUDO_OTP = 'sudo-otp'
#: Form id for sudo password form
FORMID_SUDO_PASSWORD = 'sudo-password'  # noqa: S105  # nosec

# --- Registry entries -----------------------------------------------------------------

session_timeouts['sudo_context'] = timedelta(minutes=15)


# --- Login manager --------------------------------------------------------------------


class LoginManager:
    """Compatibility login manager that resembles Flask-Lastuser."""

    # For compatibility with baseframe.forms.fields.UserSelectFieldBase
    usermanager: Type
    usermodel = User

    # Flag for Baseframe to avoid attempting API calls
    is_master_data_source = True

    @property
    def autocomplete_endpoint(self):
        """Endpoint for autocomplete of user name (used in Baseframe)."""
        return app_url_for(app, 'user_autocomplete')

    @property
    def getuser_endpoint(self):
        """Endpoint for getting a user by userid (used in Baseframe)."""
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
                # TODO: Force render of logout page to clear client-side data
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
                # TODO: Force render of logout page to clear client-side data
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
                # TODO: Force render of logout page to clear client-side data
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

# --- View helpers ---------------------------------------------------------------------


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
def clear_old_session(response: ResponseType) -> ResponseType:
    """Delete cookies that _may_ accidentally be present (and conflicting)."""
    for cookie_name, domains in app.config.get('DELETE_COOKIES', {}).items():
        if cookie_name in request.cookies:
            for domain in domains:
                response.set_cookie(
                    cookie_name, '', expires=0, httponly=True, domain=domain
                )
    return response


# Also add future hasjob app here
@app.after_request
def set_lastuser_cookie(response: ResponseType) -> ResponseType:
    """Save lastuser login cookie and hasuser JS-readable flag cookie."""
    if (
        request_has_auth()
        and hasattr(current_auth, 'cookie')
        and not (
            current_auth.cookie == {}
            and getattr(current_auth, 'suppress_empty_cookie', False)
        )
    ):
        response.vary.add('Cookie')  # type: ignore[union-attr]
        expires = utcnow() + current_app.config['PERMANENT_SESSION_LIFETIME']
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
            # the user arrives from an external site, including an OAuth2 callback.
            # We mitigate this for auth using the `@reload_for_cookies` decorator,
            # but use a Lax policy for now as (a) all POST requests are
            # CSRF-protected, and (b) an inbound link that renders for an anonymous
            # user will be confusing for a logged-in user
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
def update_user_session_timestamp(response: ResponseType) -> ResponseType:
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
            with app_context():
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


# --- Utility functions and decorators -------------------------------------------------


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


def reload_for_cookies(f: WrappedFunc) -> WrappedFunc:
    """
    Decorate a view to reload to obtain SameSite=strict cookies.

    This decorator is required for login callback and OAuth2 auth endpoints, which must
    have cookies to function. This decorator must be outer to any other decorator that
    depends on auth or session cookies::

        @route('/path')
        @reload_for_cookies
        @requires_login
        def view() -> ReturnView:
            ...
    """

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        if 'lastuser' not in request.cookies:
            add_auth_attribute('suppress_empty_cookie', True)
            attempt = request.args.get('cookiereload')
            if not attempt:
                # First attempt: reload with HTTP 303
                url = furl(request.url)
                url.args['cookiereload'] = 'r'
                return redirect(str(url), 303)
            if attempt == 'r':
                # Second attempt: reload with Meta Refresh
                url = furl(request.url)
                url.args['cookiereload'] = 'm'
                return metarefresh_redirect(str(url))
            # If both attempts fail, there is no 'lastuser' cookie forthcoming
        return f(*args, **kwargs)

    return cast(WrappedFunc, wrapper)


def requires_user_not_spammy(
    get_current: Optional[Callable[..., str]] = None
) -> ReturnDecorator:
    """Decorate a view to require the user to prove they are not likely a spammer."""

    def decorator(f: WrappedFunc) -> WrappedFunc:
        """Apply decorator using the specified :attr:`get_current` function."""

        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            """Validate user rights in a view."""
            if not current_auth.is_authenticated:
                flash(_("You need to be logged in for that page"), 'info')
                return render_redirect(
                    url_for('login', next=get_current_url()),
                    302 if request.method == 'GET' else 303,
                )
            if not current_auth.user.features.not_likely_throwaway:
                flash(_("Confirm your phone number to continue"), 'info')

                session['next'] = (
                    get_current(*args, **kwargs) if get_current else get_current_url()
                )
                return render_redirect(url_for('add_phone'), code=303)

            return f(*args, **kwargs)

        return cast(WrappedFunc, wrapper)

    return decorator


def requires_login(f: WrappedFunc) -> WrappedFunc:
    """Decorate a view to require login."""

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        add_auth_attribute('login_required', True)
        if not current_auth.is_authenticated:
            flash(_("You need to be logged in for that page"), 'info')
            return render_redirect(
                url_for('login', next=get_current_url()),
                302 if request.method == 'GET' else 303,
            )
        return f(*args, **kwargs)

    return cast(WrappedFunc, wrapper)


def requires_login_no_message(f: WrappedFunc) -> WrappedFunc:
    """
    Decorate a view to require login, without displaying a friendly message.

    Used on views where the user is informed in advance that login is required.
    """

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        add_auth_attribute('login_required', True)
        if not current_auth.is_authenticated:
            return render_redirect(
                url_for('login', next=get_current_url()),
                302 if request.method == 'GET' else 303,
            )
        return f(*args, **kwargs)

    return cast(WrappedFunc, wrapper)


def save_sudo_preference_context() -> None:
    """Save sudo preference context to cookie session before redirecting."""
    profile = getattr(g, 'profile', None)
    if profile is not None:
        session['sudo_context'] = {'type': 'profile', 'uuid_b64': profile.uuid_b64}
    else:
        session.pop('sudo_context', None)


def get_sudo_preference_context() -> Optional[Profile]:
    """Get optional preference context for sudo endpoint."""
    profile = getattr(g, 'profile', None)
    if profile is not None:
        return profile
    sudo_context = session.get('sudo_context', {})
    if sudo_context.get('type') != 'profile':
        # Only Profile context is supported at this time
        return None
    return Profile.query.filter_by(uuid_b64=sudo_context['uuid_b64']).one_or_none()


def del_sudo_preference_context() -> None:
    """Remove optional sudo preference context from cookie session."""
    session.pop('sudo_context', None)


def requires_sudo(f: WrappedFunc) -> WrappedFunc:
    """
    Decorate a view to require the current user to have re-authenticated recently.

    Renders an authentication prompt (password or OTP) within the same request if the
    URL rule supports both GET and POST, and the request does not want a HTML fragment
    or JSON response. In other cases, it redirects the user to a sudo endpoint, attempts
    to reload the same page to force a full render instead of a HTML fragment, or sends
    a JSON error response asking the client to use the sudo endpoint.
    """

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        """Prompt for re-authentication to proceed."""
        add_auth_attribute('login_required', True)
        # If the user is not logged in, require login first
        if not current_auth.is_authenticated:
            flash(_("You need to be logged in for that page"), 'info')
            return render_redirect(url_for('login', next=get_current_url()))
        if current_auth.session.has_sudo:
            # This user authenticated recently, so no intervention is required
            del_sudo_preference_context()
            return f(*args, **kwargs)

        if request_wants.json:
            # A JSON-only endpoint can't render a form, so we have to redirect the
            # browser to the ``account_sudo`` endpoint, returning after authentication.
            # That redirect will be to the client-side JavaScript equivalent of
            # `url_for('account_sudo', next=request.url)`, in particular ensuring that
            # the host page URL including the fragment identifier is used (NOT this
            # request's URL)
            save_sudo_preference_context()
            return make_response(
                jsonify(
                    status='error',
                    error='requires_sudo',
                    error_description=_("This request requires re-authentication"),
                    sudo_url=url_for('account_sudo'),  # No `?next=` here
                ),
                422,
            )

        if not GET_AND_POST.issubset(
            request.url_rule.methods  # type: ignore[union-attr]
        ):
            # This view does not support GET or POST methods, which we need. Send the
            # user off to the sudo endpoint for authentication.
            save_sudo_preference_context()
            return render_redirect(
                url_for('account_sudo', next=get_current_url()),
                302 if request.method == 'GET' else 303,
            )

        if request_wants.html_fragment:
            # If the request wanted a HTML fragment, reload as a full page to ensure the
            # authentication form is properly rendered. The current page's fragment
            # identifier cannot be preserved in this case.
            return render_redirect(request.url, 302 if request.method == 'GET' else 303)

        # We'll need a password form or an OTP form, depending on whether the user has a
        # password or contact info for an OTP. If neither are available, we'll ask them
        # to set a password on their account
        form = None

        if request.method == 'GET':
            # If the user has a password, use a password form
            if current_auth.user.pw_hash:
                # A future version may accept 2FA (U2F or TOTP) instead of a password
                form = PasswordForm(edit_user=current_auth.user)
            elif current_auth.user.has_contact_info:
                # User does not have a password but has contact info. Try to send an OTP
                # to their phone, falling back to email
                context = get_sudo_preference_context()
                userphone = current_auth.user.transport_for_sms(context=context)
                useremail = current_auth.user.default_email(context=context)
                otp_session = OtpSession.make(
                    'sudo',
                    user=current_auth.user,
                    anchor=None,
                    phone=str(userphone) if userphone else None,
                    email=str(useremail) if useremail else None,
                )
                if otp_session.send(flash_failure=False):
                    # Use OtpForm only if an OTP could be sent. Failure messages are
                    # suppressed because the fallback option is to ask the user to set a
                    # password
                    form = OtpForm(valid_otp=otp_session.otp)

            # If the user does not have a password and an OTP could not be sent (usable
            # form is None), ask the user to set a password
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
            formid = abort_null(request.form.get('form.id'))
            if formid == FORMID_SUDO_OTP:
                try:
                    otp_session = OtpSession.retrieve('sudo')
                except OtpTimeoutError:
                    # Reload the page to send another OTP
                    return render_redirect(url=request.url)
                form = OtpForm(valid_otp=otp_session.otp)
            elif formid == FORMID_SUDO_PASSWORD:
                form = PasswordForm(edit_user=current_auth.user)
            else:
                # Unknown form
                abort(422)

            # Allow 5 password or OTP guesses per 60 seconds
            validate_rate_limit('account_sudo', current_auth.user.userid, 5, 60)
            if form.validate_on_submit():
                # User has successfully authenticated. Update their sudo timestamp
                # and reload the page with a GET request, as the wrapped view may
                # need to render its own form
                current_auth.session.set_sudo()
                continue_url = session.pop('next', request.url)
                OtpSession.delete()
                db.session.commit()
                return render_redirect(continue_url)
        else:
            # Only GET and POST are supported. We may get here if the decorated view
            # supports others methods (like PUT or DELETE)
            abort(405)

        if isinstance(form, OtpForm):
            title = _("Confirm this operation with an OTP")
            formid = FORMID_SUDO_OTP
        elif isinstance(form, PasswordForm):  # type: ignore[unreachable]
            title = _("Confirm with your password to proceed")
            formid = FORMID_SUDO_PASSWORD
        else:  # pragma: no cover
            abort(500)  # This should never happen

        return render_form(
            form=form,
            title=title,
            formid=formid,
            submit=_("Confirm"),
            ajax=False,
            template='account_formlayout.html.jinja2',
        )

    return cast(WrappedFunc, wrapper)


def requires_site_editor(f: WrappedFunc) -> WrappedFunc:
    """Decorate a view to require site editor permission."""

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        add_auth_attribute('login_required', True)
        if not current_auth.user or not current_auth.user.is_site_editor:
            abort(403)
        return f(*args, **kwargs)

    return cast(WrappedFunc, wrapper)


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


def requires_client_login(f: WrappedFunc) -> WrappedFunc:
    """Decorate a view to require a client login via HTTP Basic Authorization."""

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        return result

    return cast(WrappedFunc, wrapper)


def requires_user_or_client_login(f: WrappedFunc) -> WrappedFunc:
    """
    Decorate a view to require a user or client login.

    User login should be via an auth cookie, client login via HTTP Basic Authentication.
    """

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        add_auth_attribute('login_required', True)
        # Check for user first:
        if current_auth.is_authenticated:
            return f(*args, **kwargs)
        # If user is not logged in, check for client
        result = _client_login_inner()
        if result is None:
            return f(*args, **kwargs)
        return result

    return cast(WrappedFunc, wrapper)


def requires_client_id_or_user_or_client_login(f: WrappedFunc) -> WrappedFunc:
    """
    Decorate view to require a client_id and session, or a user, or client login.

    Looks for `client_id` and session in the request args, user in an auth cookie, or
    client via HTTP Basic Authentication.
    """

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
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

    return cast(WrappedFunc, wrapper)


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
    """Logout current user (helper function)."""
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
    """Register a user account (helper function)."""
    user = User(username=username, fullname=fullname, password=password)
    if not username:
        user.username = None
    db.session.add(user)
    user_registered.send(user)
    return user


def set_loginmethod_cookie(response, value):
    """Record the login method that was used, to provide a UI hint the next time."""
    # TODO: This is deprecated now that the primary emphasis is on OTP login.
    response.set_cookie(
        'login',
        value,
        # Keep this cookie for a year
        max_age=USER_SESSION_VALIDITY_PERIOD_TOTAL_SECONDS,
        # Expire one year from now
        expires=utcnow() + USER_SESSION_VALIDITY_PERIOD,
        secure=current_app.config['SESSION_COOKIE_SECURE'],
        httponly=True,
        samesite='Lax',
    )
    return response
