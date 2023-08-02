"""Views for login, logout and account merger."""

from __future__ import annotations

import urllib.parse
from datetime import timedelta
from secrets import token_urlsafe
from typing import TYPE_CHECKING, Union

import itsdangerous
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from baseframe import _, __, forms, statsd
from baseframe.forms import render_message
from baseframe.signals import exception_catchall
from coaster.auth import current_auth
from coaster.utils import getbool, utcnow
from coaster.views import get_next_url, requestargs

from .. import app
from ..forms import (
    LoginForm,
    LoginPasswordResetException,
    LoginPasswordWeakException,
    LoginWithOtp,
    LogoutForm,
    OtpForm,
    RegisterOtpForm,
    RegisterWithOtp,
)
from ..models import (
    Account,
    AccountEmail,
    AccountEmailClaim,
    AccountExternalId,
    AuthClientCredential,
    UserSession,
    db,
    getextid,
    merge_accounts,
    sa,
)
from ..proxies import request_wants
from ..registry import (
    LoginCallbackError,
    LoginInitError,
    LoginProviderData,
    login_registry,
)
from ..serializers import crossapp_serializer
from ..signals import user_data_changed
from ..transports import TransportError, TransportRecipientError
from ..typing import ReturnView
from ..utils import abort_null
from .email import send_email_verify_link
from .helpers import app_url_for, render_redirect, session_timeouts, validate_rate_limit
from .login_session import (
    login_internal,
    logout_internal,
    register_internal,
    reload_for_cookies,
    requires_login,
    save_session_next_url,
    set_loginmethod_cookie,
)
from .otp import OtpSession, OtpTimeoutError

session_timeouts['next'] = timedelta(minutes=30)
session_timeouts['oauth_callback'] = timedelta(minutes=30)
session_timeouts['oauth_state'] = timedelta(minutes=30)
session_timeouts['merge_buid'] = timedelta(minutes=15)
session_timeouts['login_nonce'] = timedelta(minutes=1)
session_timeouts['temp_username'] = timedelta(minutes=15)

block_iframe = {'X-Frame-Options': 'SAMEORIGIN'}

LOGOUT_ERRORMSG = __("Are you trying to logout? Try again to confirm")


def get_otp_form(otp_session: OtpSession) -> Union[OtpForm, RegisterOtpForm]:
    """Return variant of OTP form depending on whether there's a user account."""
    if otp_session.user:
        form = OtpForm(valid_otp=otp_session.otp)
    else:
        form = RegisterOtpForm(valid_otp=otp_session.otp)
    return form


def render_otp_form(
    form: Union[OtpForm, RegisterOtpForm], cancel_url: str, action: str
) -> ReturnView:
    """Render OTP form."""
    form.form_nonce.data = form.form_nonce.default()
    return (
        render_template(
            'otpform.html.jinja2',
            form=form,
            formid='login-otp',
            ref_id='form-otp',
            action=action,
            submit=_("Confirm"),
            cancel_url=cancel_url,
            with_chrome=request_wants.html_fragment,  # with_chrome is a legacy name
        ),
        200,
        block_iframe,
    )


def render_login_form(form: LoginForm, action: str) -> ReturnView:
    """Render login form."""
    return (
        render_template(
            'loginform.html.jinja2',
            form=form,
            formid='passwordlogin',
            ref_id='form-passwordlogin',
            action=action,
            with_chrome=request_wants.html_fragment,  # with_chrome is a legacy name
        ),
        200,
        block_iframe,
    )


@app.route('/login', methods=['GET', 'POST'])
def login() -> ReturnView:
    """Process a login attempt."""
    # If user is already logged in, send them back
    if current_auth.is_authenticated:
        return render_redirect(get_next_url(referrer=True, session=True))

    # Remember where the user came from if it wasn't already saved.
    save_session_next_url()
    next_url = session['next']
    action_url = url_for('login', next=next_url)
    if request.args.get('modal') in ('register-modal',):
        next_url = next_url + '#' + request.args['modal']
        action_url = url_for('login', next=next_url, modal=request.args['modal'])

    loginform = LoginForm()
    loginmethod = None
    if request.method == 'GET':
        loginmethod = request.cookies.get('login')

    formid = abort_null(request.form.get('form.id'))
    if request.method == 'POST' and formid == 'passwordlogin':
        try:
            success = loginform.validate()
            # Allow 10 login attempts per hour per user (if present) or username.
            # We do rate limit check after loading the user (via .validate()) so that
            # the limit is fixed to the user and not to the username. An account with
            # multiple email addresses will allow an extended rate limit otherwise.
            # The rate limit explicitly blocks successful validation, to discourage
            # password guessing.
            validate_rate_limit(
                'login',
                ('user/' + loginform.user.uuid_b58)
                if loginform.user
                else ('username/' + loginform.username.data),
                10,
                3600,
            )
            if success:
                user = loginform.user
                if TYPE_CHECKING:
                    assert isinstance(user, Account)  # nosec
                login_internal(user, login_service='password')
                db.session.commit()
                if loginform.weak_password:
                    current_app.logger.info(
                        "Login successful for %r, but weak password detected."
                        " Possible redirect URL is '%s' after password change",
                        user,
                        session.get('next', ''),
                    )
                    flash(
                        _(
                            "You have a weak password. To ensure the safety of"
                            " your account, please choose a stronger password"
                        ),
                        category='danger',
                    )
                    return set_loginmethod_cookie(
                        render_redirect(app_url_for(app, 'change_password')),
                        'password',
                    )
                if user.password_has_expired():
                    current_app.logger.info(
                        "Login successful for %r, but password has expired."
                        " Possible redirect URL is '%s' after password change",
                        user,
                        session.get('next', ''),
                    )
                    flash(
                        _(
                            "Your password is a year old. To ensure the safety of"
                            " your account, please choose a new password"
                        ),
                        category='warning',
                    )
                    return set_loginmethod_cookie(
                        render_redirect(app_url_for(app, 'change_password')),
                        'password',
                    )
                current_app.logger.info(
                    "Login successful for %r, possible redirect URL is '%s'",
                    user,
                    session.get('next', ''),
                )
                flash(_("You are now logged in"), category='success')
                return set_loginmethod_cookie(
                    render_redirect(get_next_url(session=True)),
                    'password',
                )
        except LoginPasswordResetException:
            flash(
                _(
                    "Your account does not have a password. Please enter your phone"
                    " number or email address to request an OTP and set a new password"
                ),
                category='danger',
            )
            session['temp_username'] = loginform.username.data
            return render_redirect(url_for('reset'))
        except LoginPasswordWeakException:
            flash(
                _(
                    "Your account has a weak password. Please enter your phone number"
                    " or email address to request an OTP and set a new password"
                )
            )
            session['temp_username'] = loginform.username.data
            return render_redirect(url_for('reset'))
        except (LoginWithOtp, RegisterWithOtp):
            otp_session = OtpSession.make(
                'login',
                loginform.user,
                loginform.anchor,
                phone=loginform.new_phone,
                email=loginform.new_email,
            )
            try:
                if otp_session.send(flash_failure=False):
                    return render_otp_form(
                        get_otp_form(otp_session),
                        url_for('login', next=next_url),
                        action_url,
                    )
            except TransportRecipientError as exc:
                # If an OTP could not be sent, report the problem to the user as a form
                # validation error. The view will flow to re-rendering the original
                # login form
                loginform.username.errors.append(str(exc))
            except TransportError as exc:
                flash(str(exc), 'error')

    elif request.method == 'POST' and formid == 'login-otp':
        try:
            otp_session = OtpSession.retrieve('login')

            # Allow 5 guesses per 60 seconds
            validate_rate_limit('login_otp', otp_session.token, 5, 60)

            otp_form = get_otp_form(otp_session)
            if otp_form.validate_on_submit():
                if not otp_session.user:
                    # Register an account
                    user = register_internal(None, otp_form.fullname.data, None)
                    if TYPE_CHECKING:
                        assert isinstance(user, Account)  # nosec
                    if otp_session.email:
                        db.session.add(user.add_email(otp_session.email, primary=True))
                    if otp_session.phone:
                        db.session.add(user.add_phone(otp_session.phone, primary=True))
                    otp_session.mark_transport_active()
                    login_internal(user, login_service='otp')
                    db.session.commit()
                    current_app.logger.info(
                        "OTP registration successful for %r,"
                        " possible redirect URL is '%s'",
                        user,
                        session.get('next', ''),
                    )
                    flash(
                        _("You are now one of us. Welcome aboard!"), category='success'
                    )
                else:
                    login_internal(otp_session.user, login_service='otp')
                    db.session.commit()
                    current_app.logger.info(
                        "Login successful for %r, possible redirect URL is '%s'",
                        otp_session.user,
                        session.get('next', ''),
                    )
                    flash(_("You are now logged in"), category='success')
                OtpSession.delete()
                return set_loginmethod_cookie(
                    render_redirect(get_next_url(session=True)),
                    'otp',
                )
            return render_otp_form(
                otp_form, url_for('login', next=next_url), action_url
            )
        except OtpTimeoutError as exc:
            reason = str(exc)
            current_app.logger.info("Login OTP timed out with %s", reason)
            flash(_("The OTP has expired. Try again?"), category='error')
            return render_login_form(loginform, action_url)
    elif request.method == 'POST':
        # This should not happen. We received an incomplete form.
        abort(422)
    if request_wants.html_fragment and formid == 'passwordlogin':
        return render_login_form(loginform, action_url)

    # Default action, render the full login page
    return (
        render_template(
            'login.html.jinja2',
            form=loginform,
            lastused=loginmethod,
            login_registry=login_registry,
            formid='passwordlogin',
            ref_id='form-passwordlogin',
            title=_("Login"),
            action=action_url,
            ajax=True,
            with_chrome=request_wants.html_fragment,
        ),
        200,
        block_iframe,
    )


def logout_client() -> ReturnView:
    """Process auth client-initiated logout."""
    cred = AuthClientCredential.get(abort_null(request.args['client_id']))
    auth_client = cred.auth_client if cred is not None else None

    if (
        auth_client is None
        or not request.referrer
        or not auth_client.host_matches(request.referrer)
    ):
        # No referrer or such client, or request didn't come from the client website.
        # Possible CSRF. Don't logout and don't send them back
        flash(LOGOUT_ERRORMSG, 'danger')
        return render_redirect(url_for('account'))

    # If there is a next destination, is it in the same domain as the client?
    if 'next' in request.args:
        if not auth_client.host_matches(request.args['next']):
            # Host doesn't match. Assume CSRF and redirect to account without logout
            flash(LOGOUT_ERRORMSG, 'danger')
            return render_redirect(url_for('account'))
    # All good. Log them out and send them back
    logout_internal()
    db.session.commit()
    return render_template(
        'logout_browser_data.html.jinja2', next=get_next_url(external=True)
    )


@app.route('/logout')
def logout() -> ReturnView:
    """Inform user of deprecated logout endpoint."""
    # Logout, but protect from CSRF attempts
    if 'client_id' in request.args:
        return logout_client()
    # Don't allow GET-based logouts
    if current_auth.user:
        flash(_("To logout, use the logout button"), 'info')
        return render_redirect(url_for('account'))
    return render_redirect(url_for('index'))


@app.route('/account/logout', methods=['POST'])
@requires_login
def account_logout() -> ReturnView:
    """Process a logout request."""
    form = LogoutForm(user=current_auth.user)
    if form.validate():
        if form.user_session:
            form.user_session.revoke()
            db.session.commit()
            if request_wants.json:
                return {'status': 'ok'}
            return render_redirect(url_for('account'))

        logout_internal()
        db.session.commit()
        flash(_("You are now logged out"), category='info')
        return render_template('logout_browser_data.html.jinja2', next=get_next_url())

    if request_wants.json:
        return {'status': 'error', 'errors': form.errors}

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'error')
    return render_redirect(url_for('account'))


@app.route('/login/<service>')
def login_service(service: str) -> ReturnView:
    """Handle login with a registered service."""
    if service not in login_registry:
        abort(404)
    provider = login_registry[service]
    if not login_registry[service].at_login and not current_auth:
        abort(403)
    save_session_next_url()

    callback_url = url_for('.login_service_callback', service=service, _external=True)
    statsd.gauge('login.progress', 1, delta=True, tags={'service': service})
    try:
        return provider.do(callback_url=callback_url)
    except LoginInitError as exc:
        msg = str(exc)
        exception_catchall.send(exc, message=msg)
        flash(msg, category='danger')
        return render_redirect(session.pop('next'))


@app.route('/login/<service>/callback', methods=['GET', 'POST'])
@reload_for_cookies
def login_service_callback(service: str) -> ReturnView:
    """Handle callback from a login service."""
    if service not in login_registry:
        abort(404)

    provider = login_registry[service]
    try:
        userdata = provider.callback()
    except LoginCallbackError as exc:
        msg = _("{service} login failed: {error}").format(
            service=provider.title, error=str(exc)
        )
        exception_catchall.send(exc, message=msg)
        flash(msg, category='danger')
        if current_auth.is_authenticated:
            return render_redirect(get_next_url(referrer=False))
        return render_redirect(url_for('login'))
    statsd.gauge('login.progress', -1, delta=True, tags={'service': service})
    return login_service_postcallback(service, userdata)


def get_user_extid(service, userdata):
    """Retrieve user, extid and email from the given service and userdata."""
    provider = login_registry[service]
    extid = getextid(service=service, userid=userdata.userid)

    user = None
    accountemail = None

    if userdata.email:
        accountemail = AccountEmail.get(email=userdata.email)

    if extid is not None:
        user = extid.account
    # It is possible at this time that extid.account and accountemail.account are
    # different. We do not handle it here, but in the parent function
    # login_service_postcallback.
    elif accountemail is not None and accountemail.account is not None:
        user = accountemail.account
    else:
        # Cross-check with all other instances of the same LoginProvider (if we don't
        # have a user) This is (for eg) for when we have two Twitter services with
        # different access levels.
        for other_service, other_provider in login_registry.items():
            if (
                other_service != service
                and other_provider.__class__ == provider.__class__
            ):
                other_extid = getextid(service=other_service, userid=userdata.userid)
                if other_extid is not None:
                    user = other_extid.account
                    break

    # TODO: Make this work when we have multiple confirmed email addresses available
    return user, extid, accountemail


def login_service_postcallback(service: str, userdata: LoginProviderData) -> ReturnView:
    """
    Process callback from a login provider.

    Called from :func:`login_service_callback` after receiving data from the upstream
    login service.
    """
    # 1. Check whether we have an existing UserExternalId
    user, extid, accountemail = get_user_extid(service, userdata)
    # If extid is not None, user.extid == user, guaranteed.
    # If extid is None but accountemail is not None, user == accountemail.account
    # However, if both extid and accountemail are present, they may be different users
    if extid is not None:
        extid.oauth_token = userdata.oauth_token
        extid.oauth_token_secret = userdata.oauth_token_secret
        extid.oauth_token_type = userdata.oauth_token_type
        extid.username = userdata.username
        extid.oauth_refresh_token = userdata.oauth_refresh_token
        extid.oauth_expires_in = userdata.oauth_expires_in
        extid.oauth_expires_at = (
            (utcnow() + timedelta(seconds=userdata.oauth_expires_in))
            if userdata.oauth_expires_in
            else None
        )
        extid.last_used_at = sa.func.utcnow()
    else:
        # New external id. Register it.
        extid = AccountExternalId(
            account=user,  # This may be None right now. Will be handled below
            service=service,
            userid=userdata.userid,
            username=userdata.username,
            oauth_token=userdata.oauth_token,
            oauth_token_secret=userdata.oauth_token_secret,
            oauth_token_type=userdata.oauth_token_type,
            oauth_refresh_token=userdata.oauth_refresh_token,
            oauth_expires_in=userdata.oauth_expires_in,
            oauth_expires_at=sa.func.utcnow()
            + timedelta(seconds=userdata.oauth_expires_in)
            if userdata.oauth_expires_in
            else None,
            last_used_at=sa.func.utcnow(),
        )
    if user is None:
        if current_auth:
            # Attach this id to currently logged-in user
            user = current_auth.user
            extid.account = user
        else:
            # Register a new user
            user = register_internal(None, userdata.fullname, None)
            extid.account = user
            if userdata.username:
                if Account.is_available_name(userdata.username):
                    # Set a username for this user if it's available
                    user.username = userdata.username
    else:  # We have an existing user account from extid or accountemail
        if current_auth and current_auth.user != user:
            # Woah! Account merger handler required
            # Always confirm with user before doing an account merger
            session['merge_buid'] = user.buid
        elif accountemail and accountemail.account != user:
            # Once again, account merger required since the extid and accountemail are
            # linked to different accounts
            session['merge_buid'] = accountemail.account.buid

    # Check for new email addresses
    if userdata.email and not accountemail:
        db.session.add(user.add_email(userdata.email))

    # If there are multiple email addresses, add any that are not already claimed.
    # If they are already claimed by another user, this calls for an account merge
    # request, but we can only merge two users at a time. Ask for a merge if there
    # isn't already one pending
    if userdata.emails:
        for email in userdata.emails:
            existing = AccountEmail.get(email)
            if existing is not None:
                if existing.account != user and 'merge_buid' not in session:
                    session['merge_buid'] = existing.account.buid
            else:
                db.session.add(user.add_email(email))

    if userdata.emailclaim:
        emailclaim = AccountEmailClaim(account=user, email=userdata.emailclaim)
        db.session.add(emailclaim)
        send_email_verify_link(emailclaim)

    # Is the user's fullname missing? Populate it.
    if not user.fullname and userdata.fullname:
        user.fullname = userdata.fullname

    if not current_auth:  # If a user isn't already logged in, login now.
        login_internal(user, login_service=service)
        flash(
            _("You have logged in via {service}").format(
                service=login_registry[service].title
            ),
            'success',
        )
    next_url = get_next_url(session=True)

    db.session.add(extid)  # If we made a new extid, add it to the session now
    db.session.commit()

    # Finally: set a login method cookie and send user on their way
    if not current_auth.user.is_profile_complete():
        login_next = url_for('account_edit', next=next_url)
    else:
        login_next = next_url

    if 'merge_buid' in session:
        return set_loginmethod_cookie(
            render_redirect(url_for('account_merge', next=login_next)), service
        )
    return set_loginmethod_cookie(render_redirect(login_next), service)


@app.route('/account/merge', methods=['GET', 'POST'])
@requires_login
def account_merge() -> ReturnView:
    """Merge two accounts."""
    if 'merge_buid' not in session:
        return render_redirect(get_next_url())
    other_user = Account.get(buid=session['merge_buid'])
    if other_user is None:
        session.pop('merge_buid', None)
        return render_redirect(get_next_url())
    form = forms.Form()
    if form.validate_on_submit():
        if 'merge' in request.form:
            new_user = merge_accounts(current_auth.user, other_user)
            if new_user is not None:
                login_internal(
                    new_user,
                    login_service=current_auth.session.login_service
                    if current_auth.session
                    else None,
                )
                flash(_("Your accounts have been merged"), 'success')
                session.pop('merge_buid', None)
                db.session.commit()
                user_data_changed.send(new_user, changes=['merge'])
            else:
                flash(_("Account merger failed"), 'danger')
                session.pop('merge_buid', None)
            return render_redirect(get_next_url())
        session.pop('merge_buid', None)
        return render_redirect(get_next_url())
    return render_template(
        'account_merge.html.jinja2',
        form=form,
        user=current_auth.user,
        other_user=other_user,
        login_registry=login_registry,
        formid='mergeaccounts',
        ref_id='form-mergeaccounts',
        title=_("Merge accounts"),
    )


# --- Future Hasjob login --------------------------------------------------------------

# Hasjob login flow:

# 1. `hasjobapp` /login does:
#     1. Set nonce cookie if not already present
#     2. Create a signed request code using nonce
#     3. Redirect user to `app` /login/hasjob?code={code}

# 2. `app` /login/hasjob does:
#     1. Ask user to login if required (@requires_login(''))
#     2. Verify signature of code
#     3. Create a timestamped token using (nonce, user_session.buid)
#     4. Redirect user to `hasjobapp` /login/callback?token={token}

# 3. `hasjobapp` /login/callback does:
#     1. Verify token (signature valid, nonce valid, timestamp < 30s)
#     2. Loads user session and sets session cookie (calling login_internal)
#     3. Redirects user back to where they came from, or '/'


# Retained for future hasjob integration


# @hasjobapp.route('/login', endpoint='login')
@requestargs(('cookietest', getbool))
def hasjob_login(cookietest: bool = False) -> ReturnView:
    """Process login in Hasjob (pending future merger)."""
    # 1. Create a login nonce (single use, unlike CSRF)
    session['login_nonce'] = str(token_urlsafe())
    if not cookietest:
        # Reconstruct current URL with ?cookietest=1 or &cookietest=1 appended
        if request.query_string:
            return redirect(request.url + '&cookietest=1')
        return redirect(request.url + '?cookietest=1')

    if 'login_nonce' not in session:
        # No support for cookies. Abort login
        return render_message(
            title=_("Cookies required"),
            message=_("Please enable cookies in your browser"),
        )
    # 2. Nonce has been set. Create a request code
    request_code = crossapp_serializer().dumps({'nonce': session['login_nonce']})
    # 3. Redirect user
    return redirect(app_url_for(app, 'login_hasjob', code=request_code))


# Retained for future hasjob integration

# @app.route('/login/hasjob')
# @reload_for_cookies
# @requires_login('')  # 1. Ensure user login
# @requestargs('code')
# def login_hasjob(code):
#     """Process a request for login initiated from Hasjob."""
#     # 2. Verify signature of code
#     try:
#         request_code = crossapp_serializer().loads(code)
#     except itsdangerous.BadData:
#         current_app.logger.warning("hasjobapp login code is bad: %s", code)
#         return redirect(url_for('index'), 303)
#     # 3. Create token
#     token = crossapp_serializer().dumps(
#         {'nonce': request_code['nonce'], 'sessionid': current_auth.session.buid}
#     )
#     # 4. Redirect user
#     return redirect(app_url_for(hasjobapp, 'login_callback', token=token))


# Retained for future hasjob integration
# @hasjobapp.route('/login/callback', endpoint='login_callback')
@reload_for_cookies
@requestargs('token')
def hasjobapp_login_callback(token):
    """Process callback from Hasjob to confirm a login attempt."""
    nonce = session.pop('login_nonce', None)
    if not nonce:
        # Can't proceed if this happens
        current_app.logger.warning("hasjobapp is missing an expected login nonce")
        return render_redirect(url_for('index'))

    # 1. Verify token
    try:
        # Valid up to 30 seconds for slow connections. This is the time gap between
        # `app` returning a redirect response and user agent loading `hasjobapp`'s URL
        request_token = crossapp_serializer().loads(token, max_age=30)
    except itsdangerous.BadData:
        current_app.logger.warning("hasjobapp received bad login token: %s", token)
        flash(_("Your attempt to login failed. Try again?"), 'error')
        return render_redirect(url_for('index'))
    if request_token['nonce'] != nonce:
        current_app.logger.warning(
            "hasjobapp received invalid nonce in %r", request_token
        )
        flash(_("Are you trying to login? Try again to confirm"), 'error')
        return render_redirect(url_for('index'))

    # 2. Load user session and 3. Redirect user back to where they came from
    user_session = UserSession.get(request_token['sessionid'])
    if user_session is not None:
        user = user_session.user
        login_internal(user, user_session)
        db.session.commit()
        flash(_("You are now logged in"), category='success')
        current_app.logger.debug(
            "hasjobapp login succeeded for %r, %r", user, user_session
        )
        return render_redirect(get_next_url(session=True))

    # No user session? That shouldn't happen. Log it
    current_app.logger.warning(
        "User session is unexpectedly invalid in %r", request_token
    )
    return render_redirect(url_for('index'))


# Retained for future hasjob integration
# @hasjobapp.route('/logout', endpoint='logout')
def hasjob_logout():
    """Process a logout request in Hasjob."""
    # Revoke session and redirect to homepage. Don't bother to ask `app` to logout
    # as well since the session is revoked. `app` will notice and drop cookies on
    # the next request there

    # TODO: Change logout to a POST-based mechanism, as in the main app
    if not request.referrer or (
        urllib.parse.urlsplit(request.referrer).netloc
        != urllib.parse.urlsplit(request.url).netloc
    ):
        flash(LOGOUT_ERRORMSG, 'danger')
        return render_redirect(url_for('index'))
    logout_internal()
    db.session.commit()
    flash(_("You are now logged out"), category='info')
    return render_redirect(get_next_url())
