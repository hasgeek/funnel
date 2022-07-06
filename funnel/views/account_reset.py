"""Views to reset an account password."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from flask import (
    Markup,
    current_app,
    escape,
    flash,
    redirect,
    request,
    session,
    url_for,
)
from flask_babelhg import ngettext
import itsdangerous

from baseframe import _
from baseframe.forms import render_form, render_message
from coaster.utils import getbool
from coaster.views import requestargs

from .. import app
from ..forms import OtpForm, PasswordCreateForm, PasswordResetRequestForm
from ..models import AccountPasswordNotification, User, db
from ..registry import login_registry
from ..serializers import token_serializer
from ..typing import ReturnView
from .helpers import (
    metarefresh_redirect,
    render_redirect,
    session_timeouts,
    str_pw_set_at,
    validate_rate_limit,
)
from .login_session import logout_internal
from .notification import dispatch_notification
from .otp import OtpSession, OtpTimeoutError

session_timeouts['reset_token'] = timedelta(minutes=15)


@app.route('/account/reset', methods=['GET', 'POST'])
def reset() -> ReturnView:
    """Reset password."""
    # User wants to reset password
    # Ask for phone, email or username, verify it, and send a reset code
    form = PasswordResetRequestForm()
    if request.method == 'GET':
        form.username.data = session.get('temp_username', '')
    elif request.method == 'POST':
        # Limit use of this endpoint to probe for accounts. Allow 5 submissions per 60
        # seconds per IP address. This will let a user try a few usernames/emails in
        # quick succession, and will not block other attempts from the same IP address
        # in case it is a NAT gateway -- assuming multiple users are not trying to reset
        # at the same time -- but will limit use of the endpoint for enumeration.
        validate_rate_limit('account_reset', str(request.remote_addr), 5, 60)

    if form.validate_on_submit():
        user = form.user
        anchor = form.anchor
        if TYPE_CHECKING:
            assert isinstance(user, User)  # nosec
        if not anchor:
            # User has no phone or email. Maybe they logged in via Twitter
            # and set a local username and password, but no email. Could happen
            if len(user.externalids) > 0:
                extid = user.externalids[0]
                session.pop('temp_username', None)
                return render_message(
                    title=_("Cannot reset password"),
                    message=Markup(
                        _(
                            "Your account does not have a phone number or email"
                            " address. However, it is linked to {service} with the ID"
                            " {username}. You can use that to login"
                        ).format(
                            service=login_registry[extid.service].title,
                            username=extid.username or extid.userid,
                        )
                    ),
                )
            session.pop('temp_username', None)
            return render_message(
                title=_("Cannot reset password"),
                message=Markup(
                    _(
                        'Your account does not have a phone number or email address.'
                        ' Please contact <a href="tel:{phone}">{phone}</a> or'
                        ' <a href="mailto:{email}">{email}</a> for assistance'
                    ).format(
                        phone=escape(current_app.config['SITE_SUPPORT_PHONE']),
                        email=escape(current_app.config['SITE_SUPPORT_EMAIL']),
                    )
                ),
            )
        # Allow only three reset attempts per hour to discourage abuse
        validate_rate_limit('account_reset', user.uuid_b58, 3, 3600)
        otp_session = OtpSession.make('reset', user, anchor)
        if otp_session.send():
            session.pop('temp_username', None)
            return render_redirect(url_for('reset_otp'))

            # else: render form again, with flash messages from otp_session.send()

    return render_form(
        form=form,
        title=_("Reset password"),
        submit=_("Send OTP"),
        ajax=False,
        template='account_formlayout.html.jinja2',
    )


@app.route('/account/reset/<token>')
@requestargs(('cookietest', getbool))
def reset_with_token(token: str, cookietest=False) -> ReturnView:
    """Move token into session cookie and redirect to a token-free URL."""
    if not cookietest:
        session['reset_token'] = token
        # Reconstruct current URL with ?cookietest=1 or &cookietest=1 appended
        # and reload the page
        if request.query_string:
            return redirect(request.url + '&cookietest=1')
        return redirect(request.url + '?cookietest=1')
    if 'reset_token' not in session:  # implicit: cookietest is True
        # Browser is refusing to set cookies on 302 redirects. Set it again and use
        # the less secure meta-refresh redirect (browser extensions can read the URL)
        session['reset_token'] = token
        return metarefresh_redirect(url_for('reset_with_token_do'))
    # implicit: cookietest is True and 'reset_token' in session
    return redirect(url_for('reset_with_token_do'))


@app.route('/account/reset/<buid>/<secret>')
def reset_with_token_legacy(buid: str, secret: str) -> ReturnView:
    """Old links with separate user id and secret are no longer valid."""
    flash(
        _(
            "This password reset link is invalid."
            " If you still need to reset your password, you may request an OTP"
        ),
        'info',
    )
    return render_redirect(url_for('reset'))


@app.route('/account/reset/otp', methods=['GET', 'POST'])
def reset_otp() -> ReturnView:
    """Process a password reset using an OTP."""
    try:
        otp_session = OtpSession.retrieve('reset')
    except OtpTimeoutError:
        flash(_("This OTP has expired"), category='error')
        return render_redirect(url_for('reset'))

    form = OtpForm(valid_otp=otp_session.otp)
    if form.is_submitted():
        # Allow 5 guesses per 60 seconds
        validate_rate_limit('account_reset_otp', otp_session.token, 5, 60)
    if form.validate_on_submit():
        # If the OTP is correct, continue with the email reset link flow
        OtpSession.delete()
        return render_redirect(
            url_for(
                'reset_with_token',
                token=otp_session.link_token,
            )
        )
    return render_form(
        form=form,
        title=_("Verify OTP"),
        submit=_("Confirm"),
        ajax=False,
        template='account_formlayout.html.jinja2',
    )


@app.route('/account/reset/do', methods=['GET', 'POST'])
def reset_with_token_do() -> ReturnView:
    """Reset account password using a token in cookie session."""
    # Validate the token
    # 1. Do we have a token? User may have accidentally landed here
    if 'reset_token' not in session:
        if request.method == 'GET':
            # No token. GET request. Either user landed here by accident, or browser
            # reloaded this page from history. Send back to to the reset request page
            return render_redirect(url_for('reset'))

        # Reset token was expired from session, likely because they didn't submit
        # the form in time. We no longer know what user this is for. Inform the user
        return render_message(
            title=_("This page has timed out"),
            message=_("Open the reset link again to reset your password"),
        )

    # 2. There's a token in the session. Is it valid?
    try:
        # Allow 24 hours (86k seconds) validity for the reset token
        token = token_serializer().loads(session['reset_token'], max_age=86400)
    except itsdangerous.SignatureExpired:
        # Link has expired (timeout).
        session.pop('reset_token', None)
        flash(
            _(
                "This password reset link has expired."
                " If you still need to reset your password, you may request an OTP"
            ),
            'error',
        )
        return render_redirect(url_for('reset'))
    except itsdangerous.BadData:
        # Link is invalid
        session.pop('reset_token', None)
        flash(
            _(
                "This password reset link is invalid."
                " If you still need to reset your password, you may request an OTP"
            ),
            'error',
        )
        return render_redirect(url_for('reset'))

    # 3. We have a token and it's not expired. Is there a user?
    user = User.get(buid=token['buid'])
    if user is None:
        # If the user has disappeared, it's likely because this is a dev instance and
        # the local database has been dropped -- or a future scenario in which db entry
        # is deleted after account deletion
        session.pop('reset_token', None)
        return render_message(
            title=_("Unknown user"),
            message=_("There is no account matching this password reset request"),
        )
    # 4. We have a user. Has the token been used already? Check pw_set_at
    if token['pw_set_at'] != str_pw_set_at(user):
        # Token has been used to set a password, as the timestamp has changed. Ask user
        # if they want to reset their password again
        session.pop('reset_token', None)
        flash(
            _(
                "This password reset link has been used."
                " If you need to reset your password again, you may request an OTP"
            ),
            'error',
        )
        return render_redirect(url_for('reset'))

    # All good? Proceed with request
    # Logout *after* validating the reset request to prevent DoS attacks on the user
    logout_internal()
    db.session.commit()
    # Reset code is valid. Now ask user to choose a new password
    form = PasswordCreateForm(edit_user=user)
    if form.validate_on_submit():
        current_app.logger.info("Password strength %f", form.password_strength)
        user.password = form.password.data
        session.pop('reset_token', None)
        # Invalidate all of the user's active sessions
        user_sessions = user.active_user_sessions.all()
        session_count = len(user_sessions)
        for user_session in user_sessions:
            user_session.revoke()
        db.session.commit()
        dispatch_notification(AccountPasswordNotification(document=user))
        return render_message(
            title=_("Password reset complete"),
            message=_(
                "Your password has been changed. You may now login with your new"
                " password"
            )
            if session_count == 0
            else ngettext(
                "Your password has been changed. As a precaution, you have been logged"
                " out of one other device. You may now login with your new password",
                "Your password has been changed. As a precaution, you have been logged"
                " out of %(num)d other devices. You may now login with your new"
                " password",
                session_count,
            ),
        )
    # Form with id 'form-password-change' will have password strength meter on UI
    return render_form(
        form=form,
        title=_("Reset password"),
        formid='password-change',
        submit=_("Reset password"),
        message=Markup(
            _("Hello, {fullname}. You may now choose a new password").format(
                fullname=escape(user.fullname)
            )
        ),
        ajax=False,
        template='account_formlayout.html.jinja2',
    )
