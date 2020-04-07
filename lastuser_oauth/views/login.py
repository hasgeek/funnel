# -*- coding: utf-8 -*-

from datetime import timedelta
import urllib.parse

from flask import (
    Markup,
    abort,
    current_app,
    escape,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_openid import OpenID
from openid import oidutil

from baseframe import _, __, request_is_xhr
from baseframe.forms import render_form, render_message, render_redirect
from coaster.auth import current_auth
from coaster.utils import getbool, utcnow
from coaster.views import get_next_url, load_model
from lastuser_core import login_registry
from lastuser_core.models import (
    AuthClientCredential,
    AuthPasswordResetRequest,
    User,
    UserEmailClaim,
    UserSession,
    db,
)
from lastuser_core.utils import mask_email

from .. import lastuser_oauth
from ..forms import (
    LoginForm,
    LoginPasswordResetException,
    PasswordResetForm,
    PasswordResetRequestForm,
    RegisterForm,
)
from ..mailclient import send_email_verify_link, send_password_reset_link
from .helpers import (
    login_internal,
    logout_internal,
    register_internal,
    set_loginmethod_cookie,
)

oid = OpenID()


def openid_log(message, level=0):
    # FIXME: deprecate this along with Flask-OAuth
    if current_app.debug:
        print(message)  # noqa: T001


oidutil.log = openid_log


@lastuser_oauth.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    # If user is already logged in, send them back
    if current_auth.is_authenticated:
        return redirect(get_next_url(referrer=True), code=303)

    loginform = LoginForm()
    service_forms = {}
    for service, provider in login_registry.items():
        if provider.at_login and provider.form is not None:
            service_forms[service] = provider.get_form()

    loginmethod = None
    if request.method == 'GET':
        loginmethod = request.cookies.get('login')

    formid = request.form.get('form.id')
    if request.method == 'POST' and formid == 'passwordlogin':
        try:
            if loginform.validate():
                user = loginform.user
                login_internal(user)
                db.session.commit()
                flash(_("You are now logged in"), category='success')
                return set_loginmethod_cookie(
                    render_redirect(get_next_url(session=True), code=303), 'password'
                )
        except LoginPasswordResetException:
            flash(
                _(
                    "Your account does not have a password set. Please enter your username "
                    "or email address to request a reset code and set a new password"
                ),
                category='danger',
            )
            return render_redirect(url_for('.reset', username=loginform.username.data))
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
                'loginform.html.jinja2', loginform=loginform, Markup=Markup
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
                Markup=Markup,
                login_registry=login_registry,
            ),
            200,
            iframe_block,
        )


logout_errormsg = __(
    "We detected a possibly unauthorized attempt to log you out. "
    "If you really did intend to logout, please click on the logout link again"
)


def logout_user():
    """
    User-initiated logout
    """
    if not request.referrer or (
        urllib.parse.urlsplit(request.referrer).netloc
        != urllib.parse.urlsplit(request.url).netloc
    ):
        # TODO: present a logout form
        flash(
            current_app.config.get('LOGOUT_UNAUTHORIZED_MESSAGE') or logout_errormsg,
            'danger',
        )
        return redirect(url_for('index'))
    else:
        logout_internal()
        db.session.commit()
        flash(_("You are now logged out"), category='info')
        return redirect(get_next_url())


def logout_client():
    """
    Client-initiated logout
    """
    cred = AuthClientCredential.get(request.args['client_id'])
    auth_client = cred.auth_client if cred else None

    if (
        auth_client is None
        or not request.referrer
        or not auth_client.host_matches(request.referrer)
    ):
        # No referrer or such client, or request didn't come from the client website.
        # Possible CSRF. Don't logout and don't send them back
        flash(
            current_app.config.get('LOGOUT_UNAUTHORIZED_MESSAGE') or logout_errormsg,
            'danger',
        )
        return redirect(url_for('index'))

    # If there is a next destination, is it in the same domain as the client?
    if 'next' in request.args:
        if not auth_client.host_matches(request.args['next']):
            # Host doesn't match. Assume CSRF and redirect to index without logout
            flash(
                current_app.config.get('LOGOUT_UNAUTHORIZED_MESSAGE')
                or logout_errormsg,
                'danger',
            )
            return redirect(url_for('index'))
    # All good. Log them out and send them back
    logout_internal()
    db.session.commit()
    return redirect(get_next_url(external=True))


@lastuser_oauth.route('/logout')
def logout():

    # Logout, but protect from CSRF attempts
    if 'client_id' in request.args:
        return logout_client()
    else:
        # If this is not a logout request from a client, check if all is good.
        return logout_user()


@lastuser_oauth.route('/logout/<user_session>')
@load_model(UserSession, {'buid': 'user_session'}, 'user_session')
def logout_session(user_session):
    if (
        not request.referrer
        or (
            urllib.parse.urlsplit(request.referrer).netloc
            != urllib.parse.urlsplit(request.url).netloc
        )
        or (user_session.user != current_auth.user)
    ):
        flash(
            current_app.config.get('LOGOUT_UNAUTHORIZED_MESSAGE') or logout_errormsg,
            'danger',
        )
        return redirect(url_for('index'))

    user_session.revoke()
    db.session.commit()
    return redirect(get_next_url(referrer=True), code=303)


@lastuser_oauth.route('/register', methods=['GET', 'POST'])
def register():
    if current_auth.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    form.fullname.description = current_app.config.get('FULLNAME_REASON')
    form.email.description = current_app.config.get('EMAIL_REASON')
    if form.validate_on_submit():
        user = register_internal(None, form.fullname.data, form.password.data)
        useremail = UserEmailClaim(user=user, email=form.email.data)
        db.session.add(useremail)
        send_email_verify_link(useremail)
        login_internal(user)
        db.session.commit()
        flash(_("You are now one of us. Welcome aboard!"), category='success')
        return redirect(get_next_url(session=True), code=303)
    return render_form(
        form=form,
        title=_("Create an account"),
        formid='register',
        submit=_("Register"),
        message=current_app.config.get('CREATE_ACCOUNT_MESSAGE'),
    )


@lastuser_oauth.route('/reset', methods=['GET', 'POST'])
def reset():
    # User wants to reset password
    # Ask for username or email, verify it, and send a reset code
    form = PasswordResetRequestForm()
    if getbool(request.args.get('expired')):
        message = _(
            "Your password has expired. Please enter your username "
            "or email address to request a reset code and set a new password"
        )
    else:
        message = None

    if request.method == 'GET':
        form.username.data = request.args.get('username')

    if form.validate_on_submit():
        username = form.username.data
        user = form.user
        if '@' in username and not username.startswith('@'):
            # They provided an email address. Send reset email to that address
            email = username
        else:
            # Send to their existing address
            # User.email is a UserEmail object
            email = str(user.email)
        if not email and user.emailclaims:
            email = user.emailclaims[0].email
        if not email:
            # They don't have an email address. Maybe they logged in via Twitter
            # and set a local username and password, but no email. Could happen.
            if len(user.externalids) > 0:
                extid = user.externalids[0]
                return render_message(
                    title=_("Cannot reset password"),
                    message=Markup(
                        _(
                            """
                    We do not have an email address for your account. However, your account
                    is linked to <strong>{service}</strong> with the id <strong>{username}</strong>.
                    You can use that to login.
                    """
                        ).format(
                            service=login_registry[extid.service].title,
                            username=extid.username or extid.userid,
                        )
                    ),
                )
            else:
                return render_message(
                    title=_("Cannot reset password"),
                    message=Markup(
                        _(
                            """
                    We do not have an email address for your account and therefore cannot
                    email you a reset link. Please contact
                    <a href="mailto:{email}">{email}</a> for assistance.
                    """
                        ).format(email=escape(current_app.config['SITE_SUPPORT_EMAIL']))
                    ),
                )
        resetreq = AuthPasswordResetRequest(user=user)
        db.session.add(resetreq)
        send_password_reset_link(email=email, user=user, secret=resetreq.reset_code)
        db.session.commit()
        return render_message(
            title=_("Reset password"),
            message=_(
                """
            We sent a link to reset your password to your email address: {masked_email}.
            Please check your email. If it doesn’t arrive in a few minutes,
            it may have landed in your spam or junk folder.
            The reset link is valid for 24 hours.
            """.format(
                    masked_email=mask_email(email)
                )
            ),
        )
    return render_form(
        form=form,
        title=_("Reset password"),
        message=message,
        submit=_("Send reset code"),
        ajax=False,
    )


@lastuser_oauth.route('/reset/<buid>/<secret>', methods=['GET', 'POST'])
@load_model(User, {'buid': 'buid'}, 'user', kwargs=True)
def reset_email(user, kwargs):
    resetreq = AuthPasswordResetRequest.get(user, kwargs['secret'])
    if not resetreq:
        return render_message(
            title=_("Invalid reset link"),
            message=_("The reset link you clicked on is invalid"),
        )
    if resetreq.created_at < utcnow() - timedelta(days=1):
        # Reset code has expired (> 24 hours). Delete it
        db.session.delete(resetreq)
        db.session.commit()
        return render_message(
            title=_("Expired reset link"),
            message=_("The reset link you clicked on has expired"),
        )

    # Logout *after* validating the reset request to prevent DoS attacks on the user
    logout_internal()
    db.session.commit()
    # Reset code is valid. Now ask user to choose a new password
    form = PasswordResetForm()
    form.edit_user = user
    if form.validate_on_submit():
        user.password = form.password.data
        db.session.delete(resetreq)
        db.session.commit()
        return render_message(
            title=_("Password reset complete"),
            message=Markup(
                _(
                    "Your password has been reset. You may now <a href=\"{loginurl}\">login</a> with your new password."
                ).format(loginurl=escape(url_for('.login')))
            ),
        )
    return render_form(
        form=form,
        title=_("Reset password"),
        formid='reset',
        submit=_("Reset password"),
        message=Markup(
            _(
                "Hello, <strong>{fullname}</strong>. You may now choose a new password."
            ).format(fullname=escape(user.fullname))
        ),
        ajax=False,
    )
