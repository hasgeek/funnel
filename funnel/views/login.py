import urllib.parse
import uuid

from flask import (
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import itsdangerous

from baseframe import _, __, forms, request_is_xhr
from baseframe.forms import render_message, render_redirect
from baseframe.signals import exception_catchall
from coaster.auth import current_auth
from coaster.utils import getbool
from coaster.views import get_next_url, requestargs

from .. import app, funnelapp, lastuserapp
from ..forms import (
    LoginForm,
    LoginPasswordResetException,
    LoginPasswordWeakException,
    LogoutForm,
    RegisterForm,
)
from ..models import (
    AuthClientCredential,
    Profile,
    User,
    UserEmail,
    UserEmailClaim,
    UserExternalId,
    UserSession,
    db,
    getextid,
    merge_users,
)
from ..registry import LoginCallbackError, LoginInitError, login_registry
from ..serializers import talkfunnel_serializer
from ..signals import user_data_changed
from ..utils import abort_null
from .email import send_email_verify_link
from .helpers import app_url_for, metarefresh_redirect, validate_rate_limit
from .login_session import (
    login_internal,
    logout_internal,
    register_internal,
    requires_login,
    requires_login_no_message,
    set_loginmethod_cookie,
)


@app.route('/login', methods=['GET', 'POST'])
@lastuserapp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, send them back
    if current_auth.is_authenticated:
        return redirect(get_next_url(referrer=True), code=303)

    # Remember where the user came from if it wasn't already saved.
    # Placing this inside an `if` block has consequences:
    # 1. If the user aborts this login attempt but tries to login later using the login
    #    button, they will be redirected to the page the original attempt was made from,
    #    not the latest attempt. This can be unexpected behaviour. However, this problem
    #    does not exist for pages guarded with @requires_login as `next` is always saved
    #    in there.
    # 2. Browsers are increasingly tending towards stripping the referrer header. It is
    #    becoming the norm for cross-site referrers, and an OAuth2 login via /auth is
    #    crucially dependent on receiving the next URL from the client, validating it
    #    and saving to session['next'] (to avoid URL length limitations in browsers when
    #    bounce the user off to a third party login provider like Google). This saved
    #    value absolutely cannot be clobbered by the referrer header.
    # TODO: Work out a more robust solution that saves _two_ possible next URL values
    # to the session.

    if 'next' not in session:
        session['next'] = get_next_url(referrer=True)

    loginform = LoginForm()
    service_forms = {}
    for service, provider in login_registry.items():
        if provider.at_login and provider.form is not None:
            service_forms[service] = provider.get_form()

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
                login_internal(user, login_service='password')
                db.session.commit()
                if loginform.weak_password:
                    current_app.logger.info(
                        "Login successful for %r, but weak password detected. "
                        "Possible redirect URL is '%s' after password change",
                        user,
                        session.get('next', ''),
                    )
                    flash(
                        _(
                            "You have a weak password. To ensure the safety of "
                            "your account, please choose a stronger password"
                        ),
                        category='danger',
                    )
                    return set_loginmethod_cookie(
                        render_redirect(app_url_for(app, 'change_password'), code=303),
                        'password',
                    )
                elif user.password_has_expired():
                    current_app.logger.info(
                        "Login successful for %r, but password has expired. "
                        "Possible redirect URL is '%s' after password change",
                        user,
                        session.get('next', ''),
                    )
                    flash(
                        _(
                            "Your password is a year old. To ensure the safety of "
                            "your account, please choose a new password"
                        ),
                        category='warning',
                    )
                    return set_loginmethod_cookie(
                        render_redirect(app_url_for(app, 'change_password'), code=303),
                        'password',
                    )
                else:
                    current_app.logger.info(
                        "Login successful for %r, possible redirect URL is '%s'",
                        user,
                        session.get('next', ''),
                    )
                    flash(_("You are now logged in"), category='success')
                    return set_loginmethod_cookie(
                        render_redirect(get_next_url(session=True), code=303),
                        'password',
                    )
        except LoginPasswordResetException:
            flash(
                _(
                    "Your account does not have a password set. Please enter your "
                    "username or email address to request a reset code and set a "
                    "new password"
                ),
                category='danger',
            )
            return render_redirect(
                url_for('reset', username=loginform.username.data), code=303
            )
        except LoginPasswordWeakException:
            flash(
                _(
                    "Your account has a weak password. Please enter your "
                    "username or email address to request a reset code and set a "
                    "new password"
                )
            )
            return render_redirect(
                url_for('reset', username=loginform.username.data), code=303
            )
    elif request.method == 'POST' and formid in service_forms:
        form = service_forms[formid]['form']
        if form.validate():
            return set_loginmethod_cookie(login_registry[formid].do(form=form), formid)
    elif request.method == 'POST':
        abort(500)
    iframe_block = {'X-Frame-Options': 'SAMEORIGIN'}
    if request_is_xhr() and formid == 'passwordlogin':
        return (
            render_template(
                'loginform.html.jinja2',
                loginform=loginform,
                ref_id='form-passwordlogin',
            ),
            200,
            iframe_block,
        )
    else:
        return (
            render_template(
                'login.html.jinja2',
                loginform=loginform,
                lastused=loginmethod,
                service_forms=service_forms,
                login_registry=login_registry,
                formid='passwordlogin',
                ref_id='form-passwordlogin',
                title=_("Login"),
            ),
            200,
            iframe_block,
        )


logout_errormsg = __("Are you trying to logout? Please try again to confirm")


def logout_client():
    """
    Client-initiated logout
    """
    cred = AuthClientCredential.get(abort_null(request.args['client_id']))
    auth_client = cred.auth_client if cred else None

    if (
        auth_client is None
        or not request.referrer
        or not auth_client.host_matches(request.referrer)
    ):
        # No referrer or such client, or request didn't come from the client website.
        # Possible CSRF. Don't logout and don't send them back
        flash(logout_errormsg, 'danger')
        return redirect(url_for('account'), code=303)

    # If there is a next destination, is it in the same domain as the client?
    if 'next' in request.args:
        if not auth_client.host_matches(request.args['next']):
            # Host doesn't match. Assume CSRF and redirect to account without logout
            flash(logout_errormsg, 'danger')
            return redirect(url_for('account'), code=303)
    # All good. Log them out and send them back
    logout_internal()
    db.session.commit()
    return redirect(get_next_url(external=True), code=303)


@app.route('/logout')
@lastuserapp.route('/logout')
def logout():

    # Logout, but protect from CSRF attempts
    if 'client_id' in request.args:
        return logout_client()
    else:
        # Don't allow GET-based logouts
        if current_auth.user:
            flash(_("To logout, use the logout button"), 'info')
            return redirect(url_for('account'), code=303)
        else:
            return redirect(url_for('index'), code=303)


@app.route('/account/logout', methods=['POST'])
@lastuserapp.route('/account/logout', methods=['POST'])
@requires_login
def account_logout():
    form = LogoutForm(user=current_auth.user)
    if form.validate():
        if form.user_session:
            form.user_session.revoke()
            db.session.commit()
            if request_is_xhr():
                return {'status': 'ok'}
            return redirect(url_for('account'), code=303)

        logout_internal()
        db.session.commit()
        flash(_("You are now logged out"), category='info')
        return make_response(
            render_template('logout_browser_data.html.jinja2', next=get_next_url())
        )

    if request_is_xhr():
        return {'status': 'error', 'errors': list(form.errors.values())}

    for error in form.errors.values():
        flash(error, 'error')
    return redirect(url_for('account'), code=303)


@app.route('/account/register', methods=['GET', 'POST'])
@lastuserapp.route('/register', methods=['GET', 'POST'])
def register():
    if current_auth.is_authenticated:
        return redirect(url_for('index'), code=303)
    form = RegisterForm()
    if form.validate_on_submit():
        current_app.logger.info("Password strength %f", form.password_strength)
        user = register_internal(None, form.fullname.data, form.password.data)
        useremail = UserEmailClaim(user=user, email=form.email.data)
        db.session.add(useremail)
        send_email_verify_link(useremail)
        login_internal(user, login_service='password')
        db.session.commit()
        flash(_("You are now one of us. Welcome aboard!"), category='success')
        return redirect(get_next_url(session=True), code=303)
    # Form with id 'form-password-change' will have password strength meter on UI
    return render_template(
        'signup_form.html.jinja2',
        form=form,
        login_registry=login_registry,
        title=_("Register account"),
        formid='registeraccount',
        ref_id='form-password-change',
    )


@app.route('/login/<service>', methods=['GET', 'POST'])
@lastuserapp.route('/login/<service>', methods=['GET', 'POST'])
def login_service(service):
    """
    Handle login with a registered service.
    """
    if service not in login_registry:
        abort(404)
    provider = login_registry[service]
    next_url = get_next_url(referrer=False, default=None)
    callback_url = url_for(
        '.login_service_callback', service=service, next=next_url, _external=True
    )
    try:
        return provider.do(callback_url=callback_url)
    except (LoginInitError, LoginCallbackError) as e:
        msg = _("{service} login failed: {error}").format(
            service=provider.title, error=str(e)
        )
        exception_catchall.send(e, message=msg)
        flash(msg, category='danger')
        return redirect(next_url or get_next_url(referrer=True), code=303)


@app.route('/login/<service>/callback', methods=['GET', 'POST'])
@lastuserapp.route('/login/<service>/callback', methods=['GET', 'POST'])
def login_service_callback(service):
    """
    Callback handler for a login service.
    """
    if service not in login_registry:
        abort(404)
    provider = login_registry[service]
    try:
        userdata = provider.callback()
    except (LoginInitError, LoginCallbackError) as e:
        msg = _("{service} login failed: {error}").format(
            service=provider.title, error=str(e)
        )
        exception_catchall.send(e, message=msg)
        flash(msg, category='danger')
        if current_auth.is_authenticated:
            return redirect(get_next_url(referrer=False), code=303)
        else:
            return redirect(url_for('login'), code=303)
    return login_service_postcallback(service, userdata)


def get_user_extid(service, userdata):
    """
    Retrieves a 'user', 'extid' and 'useremail' from the given service and userdata.
    """
    provider = login_registry[service]
    extid = getextid(service=service, userid=userdata['userid'])

    user = None
    useremail = None

    if userdata.get('email'):
        useremail = UserEmail.get(email=userdata['email'])

    if extid is not None:
        user = extid.user
    # It is possible at this time that extid.user and useremail.user are different.
    # We do not handle it here, but in the parent function login_service_postcallback.
    elif useremail is not None and useremail.user is not None:
        user = useremail.user
    else:
        # Cross-check with all other instances of the same LoginProvider (if we don't
        # have a user) This is (for eg) for when we have two Twitter services with
        # different access levels.
        for other_service, other_provider in login_registry.items():
            if (
                other_service != service
                and other_provider.__class__ == provider.__class__
            ):
                other_extid = getextid(service=other_service, userid=userdata['userid'])
                if other_extid is not None:
                    user = other_extid.user
                    break

    # TODO: Make this work when we have multiple confirmed email addresses available
    return user, extid, useremail


def login_service_postcallback(service, userdata):
    """
    Called from :func:`login_service_callback` after receiving data from the upstream
    login service
    """
    # 1. Check whether we have an existing UserExternalId
    user, extid, useremail = get_user_extid(service, userdata)
    # If extid is not None, user.extid == user, guaranteed.
    # If extid is None but useremail is not None, user == useremail.user
    # However, if both extid and useremail are present, they may be different users

    if extid is not None:
        extid.oauth_token = userdata.get('oauth_token')
        extid.oauth_token_secret = userdata.get('oauth_token_secret')
        extid.oauth_token_type = userdata.get('oauth_token_type')
        extid.username = userdata.get('username')
        # TODO: Save refresh token and expiry date where present
        extid.oauth_refresh_token = userdata.get('oauth_refresh_token')
        extid.oauth_expiry_date = userdata.get('oauth_expiry_date')
        extid.oauth_refresh_expiry = userdata.get(
            'oauth_refresh_expiry'
        )  # TODO: Check this
        extid.last_used_at = db.func.utcnow()
    else:
        # New external id. Register it.
        extid = UserExternalId(
            user=user,  # This may be None right now. Will be handled below
            service=service,
            userid=userdata['userid'],
            username=userdata.get('username'),
            oauth_token=userdata.get('oauth_token'),
            oauth_token_secret=userdata.get('oauth_token_secret'),
            oauth_token_type=userdata.get('oauth_token_type'),
            last_used_at=db.func.utcnow()
            # TODO: Save refresh token
        )

    if user is None:
        if current_auth:
            # Attach this id to currently logged-in user
            user = current_auth.user
            extid.user = user
        else:
            # Register a new user
            user = register_internal(None, userdata.get('fullname'), None)
            extid.user = user
            if userdata.get('username'):
                if Profile.is_available_name(userdata['username']):
                    # Set a username for this user if it's available
                    user.username = userdata['username']
    else:  # We have an existing user account from extid or useremail
        if current_auth and current_auth.user != user:
            # Woah! Account merger handler required
            # Always confirm with user before doing an account merger
            session['merge_buid'] = user.buid
        elif useremail and useremail.user != user:
            # Once again, account merger required since the extid and useremail are
            # linked to different users
            session['merge_buid'] = useremail.user.buid

    # Check for new email addresses
    if userdata.get('email') and not useremail:
        user.add_email(userdata['email'])

    # If there are multiple email addresses, add any that are not already claimed.
    # If they are already claimed by another user, this calls for an account merge
    # request, but we can only merge two users at a time. Ask for a merge if there
    # isn't already one pending
    if userdata.get('emails'):
        for email in userdata['emails']:
            existing = UserEmail.get(email)
            if existing:
                if existing.user != user and 'merge_buid' not in session:
                    session['merge_buid'] = existing.user.buid
            else:
                user.add_email(email)

    if userdata.get('emailclaim'):
        emailclaim = UserEmailClaim(user=user, email=userdata['emailclaim'])
        db.session.add(emailclaim)
        send_email_verify_link(emailclaim)

    # Is the user's fullname missing? Populate it.
    if not user.fullname and userdata.get('fullname'):
        user.fullname = userdata['fullname']

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
        login_next = url_for('account_new', next=next_url)
    else:
        login_next = next_url

    # Use a meta-refresh redirect because some versions of Firefox and Safari will
    # not set cookies in a 30x redirect if the first redirect in the sequence originated
    # on another domain. Our redirect chain is provider -> callback -> destination page.
    if 'merge_buid' in session:
        return set_loginmethod_cookie(
            metarefresh_redirect(url_for('account_merge', next=login_next)), service
        )
    else:
        return set_loginmethod_cookie(metarefresh_redirect(login_next), service)


@app.route('/account/merge', methods=['GET', 'POST'])
@lastuserapp.route('/account/merge', methods=['GET', 'POST'])
@requires_login
def account_merge():
    if 'merge_buid' not in session:
        return redirect(get_next_url(), code=303)
    other_user = User.get(buid=session['merge_buid'])
    if other_user is None:
        session.pop('merge_buid', None)
        return redirect(get_next_url(), code=303)
    form = forms.Form()
    if form.validate_on_submit():
        if 'merge' in request.form:
            new_user = merge_users(current_auth.user, other_user)
            if new_user:
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
            return redirect(get_next_url(), code=303)
        else:
            session.pop('merge_buid', None)
            return redirect(get_next_url(), code=303)
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


# --- Talkfunnel login -----------------------------------------------------------------

# Talkfunnel login flow:

# 1. `funnelapp` /login does:
#     1. Set nonce cookie if not already present
#     2. Create a signed request code using nonce
#     3. Redirect user to `app` /login/talkfunnel?code={code}

# 2. `app` /login/talkfunnel does:
#     1. Ask user to login if required (@requires_login_no_message)
#     2. Verify signature of code
#     3. Create a timestamped token using (nonce, user_session.buid)
#     4. Redirect user to `funnelapp` /login/callback?token={token}

# 3. `funnelapp` /login/callback does:
#     1. Verify token (signature valid, nonce valid, timestamp < 30s)
#     2. Loads user session and sets session cookie (calling login_internal)
#     3. Redirects user back to where they came from, or '/'


@funnelapp.route('/login', endpoint='login')
@requestargs(('cookietest', getbool))
def funnelapp_login(cookietest=False):
    # 1. Create a login nonce (single use, unlike CSRF)
    session['login_nonce'] = str(uuid.uuid4())
    if not cookietest:
        # Reconstruct current URL with ?cookietest=1 or &cookietest=1 appended
        if request.query_string:
            return redirect(request.url + '&cookietest=1')
        return redirect(request.url + '?cookietest=1')

    if 'login_nonce' not in session:
        # No support for cookies. Abort login
        return render_message(
            title=_("Cookies required"),
            message=_("Please enable cookies in your browser."),
        )
    # 2. Nonce has been set. Create a request code
    request_code = talkfunnel_serializer().dumps({'nonce': session['login_nonce']})
    # 3. Redirect user
    return redirect(app_url_for(app, 'login_talkfunnel', code=request_code))


@app.route('/login/talkfunnel')
@requires_login_no_message  # 1. Ensure user login
@requestargs('code')
def login_talkfunnel(code):
    # 2. Verify signature of code
    try:
        request_code = talkfunnel_serializer().loads(code)
    except itsdangerous.exc.BadData:
        current_app.logger.warning("funnelapp login code is bad: %s", code)
        return redirect(url_for('index'))
    # 3. Create token
    token = talkfunnel_serializer().dumps(
        {'nonce': request_code['nonce'], 'sessionid': current_auth.session.buid}
    )
    # 4. Redirect user
    return redirect(app_url_for(funnelapp, 'login_callback', token=token))


@funnelapp.route('/login/callback', endpoint='login_callback')
@requestargs('token')
def funnelapp_login_callback(token):
    nonce = session.pop('login_nonce', None)
    if not nonce:
        # Can't proceed if this happens
        current_app.logger.warning("funnelapp is missing an expected login nonce")
        return redirect(url_for('index'), code=303)

    # 1. Verify token
    try:
        # Valid up to 30 seconds for slow connections. This is the time gap between
        # `app` returning a redirect response and user agent loading `funnelapp`'s URL
        request_token = talkfunnel_serializer().loads(token, max_age=30)
    except itsdangerous.exc.BadData:
        current_app.logger.warning("funnelapp received bad login token: %s", token)
        flash(_("Your attempt to login failed. Please try again"), 'error')
        return metarefresh_redirect(url_for('index'))
    if request_token['nonce'] != nonce:
        current_app.logger.warning(
            "funnelapp received invalid nonce in %r", request_token
        )
        flash(_("If you were attempting to login, please try again"), 'error')
        return metarefresh_redirect(url_for('index'))

    # 2. Load user session and 3. Redirect user back to where they came from
    user_session = UserSession.get(request_token['sessionid'])
    if user_session:
        user = user_session.user
        login_internal(user, user_session)
        db.session.commit()
        flash(_("You are now logged in"), category='success')
        current_app.logger.debug(
            "funnelapp login succeeded for %r, %r", user, user_session
        )
        return metarefresh_redirect(get_next_url(session=True))

    # No user session? That shouldn't happen. Log it
    current_app.logger.warning(
        "User session is unexpectedly invalid in %r", request_token
    )
    return redirect(url_for('index'))


@funnelapp.route('/logout', endpoint='logout')
def funnelapp_logout():
    # Revoke session and redirect to homepage. Don't bother to ask `app` to logout
    # as well since the session is revoked. `app` will notice and drop cookies on
    # the next request there

    # TODO: Change logout to a POST-based mechanism, as in the main app
    if not request.referrer or (
        urllib.parse.urlsplit(request.referrer).netloc
        != urllib.parse.urlsplit(request.url).netloc
    ):
        flash(logout_errormsg, 'danger')
        return redirect(url_for('index'), code=303)
    else:
        logout_internal()
        db.session.commit()
        flash(_("You are now logged out"), category='info')
        return redirect(get_next_url(), code=303)
