from datetime import datetime, timedelta

from flask import (
    Markup,
    current_app,
    escape,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import itsdangerous

from flask_babelhg import ngettext
from pytz import utc

from baseframe import _
from baseframe.forms import render_form, render_message
from coaster.utils import getbool
from coaster.views import requestargs

from .. import app, lastuserapp
from ..forms import PasswordResetForm, PasswordResetRequestForm
from ..models import User, db
from ..registry import login_registry
from ..utils import abort_null, mask_email
from .email import send_password_reset_link
from .helpers import validate_rate_limit
from .login_session import logout_internal


def str_pw_set_at(user):
    """Render user.pw_set_at as a string, for comparison."""
    if user.pw_set_at is not None:
        return user.pw_set_at.astimezone(utc).replace(microsecond=0).isoformat()
    return 'None'


@app.route('/account/reset', methods=['GET', 'POST'])
@lastuserapp.route('/reset', methods=['GET', 'POST'])
def reset():
    # User wants to reset password
    # Ask for username or email, verify it, and send a reset code
    form = PasswordResetRequestForm()
    if getbool(request.args.get('expired')):
        message = _(
            "Your password has expired. Please enter your username or email address to"
            " request a reset code and set a new password."
        )
    else:
        message = None

    if request.method == 'GET':
        form.username.data = abort_null(request.args.get('username'))

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
                            "Your account does not have an email address. However,"
                            " it is linked to <strong>{service}</strong> with the id"
                            " <strong>{username}</strong>. You can use that to login."
                        ).format(
                            service=login_registry[extid.service].title,
                            username=extid.username or extid.userid,
                        )
                    ),
                )

            return render_message(
                title=_("Cannot reset password"),
                message=Markup(
                    _(
                        'Your account does not have an email address. Please'
                        ' contact <a href="mailto:{email}">{email}</a> for'
                        ' assistance.'
                    ).format(email=escape(current_app.config['SITE_SUPPORT_EMAIL']))
                ),
            )

        # Allow only two reset attempts per hour to discourage abuse
        validate_rate_limit('email_reset', user.uuid_b58, 2, 3600)
        send_password_reset_link(
            email=email,
            user=user,
            token=app.email_serializer.dumps(
                {'buid': user.buid, 'pw_set_at': str_pw_set_at(user)}
            ),
        )
        return render_message(
            title=_("Email sent"),
            message=_(
                "You have been sent an email with a link to reset your password, to"
                " your address {masked_email}. If it doesn’t arrive in a few minutes,"
                " it may have landed in your spam or junk folder. The reset link is"
                " valid for 24 hours."
            ).format(masked_email=mask_email(email)),
        )
    return render_form(
        form=form,
        title=_("Reset password"),
        message=message,
        submit=_("Send reset link"),
        ajax=False,
        template='account_formlayout.html.jinja2',
    )


@app.route('/account/reset/<token>')
@lastuserapp.route('/reset/<token>')
@requestargs(('cookietest', getbool))
def reset_email(token, cookietest=False):
    """Move token into session cookie and redirect to a token-free URL."""
    session['reset_token'] = token
    # Use naive datetime as the session can't handle tz-aware datetimes
    session['reset_token_at'] = datetime.utcnow()
    if not cookietest:
        # Reconstruct current URL with ?cookietest=1 or &cookietest=1 appended
        # and reload the page
        if request.query_string:
            return redirect(request.url + '&cookietest=1')
        return redirect(request.url + '?cookietest=1')
    if 'reset_token' not in session:
        # Browser is refusing to set cookies on 302 redirects. Set it again and use
        # the less secure meta-refresh redirect (browser extensions can read the URL)
        session['reset_token'] = token
        session['reset_token_at'] = datetime.utcnow()
        return render_template(
            'meta_refresh.html.jinja2', url=url_for('reset_email_do')
        )
    return redirect(url_for('reset_email_do'))


@app.before_request
@lastuserapp.before_request
def clear_expired_reset_token():
    """Clear reset_token from session if it's not used (user abandoned the attempt)."""
    if 'reset_token_at' in session:
        # Use naive datetime as the session can't handle tz-aware datetimes
        # Give the user 10 minutes to submit the password form.
        if session['reset_token_at'] < datetime.utcnow() - timedelta(minutes=10):
            session.pop('reset_token', None)
            session.pop('reset_token_at', None)
            current_app.logger.info("Cleared expired reset_token from session cookie")


@app.route('/account/reset/<buid>/<secret>')
@lastuserapp.route('/reset/<buid>/<secret>')
def reset_email_legacy(buid, secret):
    flash(
        _(
            "This password reset link is invalid."
            " If you still need to reset your password, you may request a new link"
        ),
        'info',
    )
    return redirect(url_for('reset'), code=303)


@app.route('/account/reset/do', methods=['GET', 'POST'])
@lastuserapp.route('/reset/do', methods=['GET', 'POST'])
def reset_email_do():

    # Validate the token
    # 1. Do we have a token? User may have accidentally landed here
    if 'reset_token' not in session:
        if request.method == 'GET':
            # No token. GET request. Either user landed here by accident, or browser
            # reloaded this page from history. Send back to to the reset request page
            return redirect(url_for('reset'), code=303)

        # Reset token was expired from session, likely because they didn't submit
        # the form in time. We no longer know what user this is for. Inform the user
        return render_message(
            title=_("Please try again"),
            message=_("This page timed out. Please open the reset link again."),
        )

    # 2. There's a token in the session. Is it valid?
    try:
        # Allow 24 hours (86k seconds) validity for the reset token
        token = app.email_serializer.loads(session['reset_token'], max_age=86400)
    except itsdangerous.exc.SignatureExpired:
        # Link has expired (timeout).
        session.pop('reset_token', None)
        session.pop('reset_token_at', None)
        flash(
            _(
                "This password reset link has expired."
                " If you still need to reset your password, you may request a new link"
            ),
            'error',
        )
        return redirect(url_for('reset'), code=303)
    except itsdangerous.exc.BadData:
        # Link is invalid
        session.pop('reset_token', None)
        session.pop('reset_token_at', None)
        flash(
            _(
                "This password reset link is invalid."
                " If you still need to reset your password, you may request a new link"
            ),
            'error',
        )
        return redirect(url_for('reset'), code=303)

    # 3. We have a token and it's not expired. Is there a user?
    user = User.get(buid=token['buid'])
    if not user:
        # If the user has disappeared, it's likely because of account deletion.
        session.pop('reset_token', None)
        session.pop('reset_token_at', None)
        return render_message(
            title=_("Unknown user"),
            message=_("There is no account matching this password reset request"),
        )
    # 4. We have a user. Has the token been used already? Check pw_set_at
    if token['pw_set_at'] != str_pw_set_at(user):
        # Token has been used to set a password, as the timestamp has changed. Ask user
        # if they want to reset their password again
        session.pop('reset_token', None)
        session.pop('reset_token_at', None)
        flash(
            _(
                "This password reset link has been used."
                " If you need to reset your password again, you may request a new link"
            ),
            'error',
        )
        return redirect(url_for('reset'), code=303)

    # All good? Proceed with request
    # Logout *after* validating the reset request to prevent DoS attacks on the user
    logout_internal()
    db.session.commit()
    # Reset code is valid. Now ask user to choose a new password
    form = PasswordResetForm()
    form.edit_user = user
    if form.validate_on_submit():
        current_app.logger.info("Password strength %f", form.password_strength)
        user.password = form.password.data
        session.pop('reset_token', None)
        session.pop('reset_token_at', None)
        # Invalidate all of the user's active sessions
        counter = None
        for counter, user_session in enumerate(user.active_sessions.all()):
            user_session.revoke()
        db.session.commit()
        return render_message(
            title=_("Password reset complete"),
            message=_(
                "Your password has been changed. You may now login with your new"
                " password."
            )
            if counter is None
            else ngettext(
                "Your password has been changed. As a precaution, you have been logged"
                " out of one other device. You may now login with your new password.",
                "Your password has been changed. As a precaution, you have been logged"
                " out of %(num)d other devices. You may now login with your new"
                " password.",
                counter + 1,
            ),
        )
    # Form with id 'form-password-change' will have password strength meter on UI
    return render_form(
        form=form,
        title=_("Reset password"),
        formid='password-change',
        submit=_("Reset password"),
        message=Markup(
            _(
                "Hello, <strong>{fullname}</strong>. You may now choose a new password."
            ).format(fullname=escape(user.fullname))
        ),
        ajax=False,
        template='account_formlayout.html.jinja2',
    )
