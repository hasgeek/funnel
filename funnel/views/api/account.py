from __future__ import annotations

from flask import request

from baseframe import _
from coaster.auth import current_auth
from coaster.views import render_with

from ... import app
from ...forms import PasswordPolicyForm, UsernameAvailableForm
from ...models import check_password_strength
from ...typing import ReturnRenderWith
from ..helpers import progressive_rate_limit_validator, validate_rate_limit


@app.route('/api/1/account/password_policy', methods=['POST'])
@render_with(json=True)
def password_policy_check() -> ReturnRenderWith:
    """Check if a password meets policy criteria (strength, embedded personal info)."""
    policy_form = PasswordPolicyForm()
    policy_form.form_nonce.data = policy_form.form_nonce.default()

    if policy_form.validate_on_submit():
        user_inputs = []

        if current_auth.user:
            if current_auth.user.fullname:
                user_inputs.append(current_auth.user.fullname)

            for useremail in current_auth.user.emails:
                user_inputs.append(str(useremail))
            for emailclaim in current_auth.user.emailclaims:
                user_inputs.append(str(emailclaim))

            for userphone in current_auth.user.phones:
                user_inputs.append(str(userphone))
            for phoneclaim in current_auth.user.phoneclaims:
                user_inputs.append(str(phoneclaim))

        tested_password = check_password_strength(
            policy_form.password.data,
            user_inputs=user_inputs if user_inputs else None,
        )
        return {
            'status': 'ok',
            'result': {
                # zxcvbn scores are 0-4, frond-end expects strength value from 0.0-1.0.
                # Keeping the backend score to backend will let us switch strength
                # calculations later on.
                'strength': tested_password['score'] / 4.0,
                'is_weak': tested_password['is_weak'],
                'strength_verbose': (
                    _("Weak password")
                    if tested_password['is_weak']
                    else _("Strong password")
                ),
                'warning': tested_password['warning'],
                'suggestions': tested_password['suggestions'],
            },
        }
    return {
        'status': 'error',
        'error_code': 'policy_form_error',
        'error_description': _("Something went wrong. Please reload and try again"),
        'error_details': policy_form.errors,
    }, 422


@app.route('/api/1/account/username_available', methods=['POST'])
@render_with(json=True)
def account_username_availability() -> ReturnRenderWith:
    """Check whether a username is available for the taking."""
    form = UsernameAvailableForm(edit_user=current_auth.user)
    del form.form_nonce

    # FIXME: Rate limiting must happen _before_ hitting the database.

    # This view does not use the simpler ``if form.validate()`` construct because
    # we need to insert the rate limiter _between_ the other validators. This will be
    # simpler if :func:`validate_rate_limit` is repositioned as a form validator rather
    # than a view validator.
    form_validate = form.validate()

    if not form_validate:
        # If no username is supplied, return a 422 Unprocessable Entity
        if not form.username.data:
            return {
                'status': 'error',
                'error': 'username_required',
            }, 422

        # Require CSRF validation to prevent this endpoint from being used by a scraper.
        # Field will be missing in a test environment, so use hasattr
        if hasattr(form, 'csrf_token') and form.csrf_token.errors:
            return {
                'status': 'error',
                'error': 'csrf_token',
            }, 422

    # Allow user or source IP to check for up to 20 usernames every 10 minutes (600s)
    validate_rate_limit(
        'account_username_available',
        current_auth.actor.uuid_b58 if current_auth.actor else request.remote_addr,
        # 20 username candidates
        20,
        # per every 10 minutes (600s)
        600,
        # Use a token and validator to count progressive typing and backspacing as a
        # single rate-limited call
        token=form.username.data,
        validator=progressive_rate_limit_validator,
    )

    # Validate form
    if form_validate:
        # All okay? Username is available
        return {'status': 'ok'}

    # If username is supplied but invalid, return HTTP 200 with an error message.
    # 400/422 is the wrong code as the request is valid and the error is app content
    return {
        'status': 'error',
        'error': 'validation_failure',
        # Use the first known error as the description
        'error_description': (
            str(form.username.errors[0])
            if form.username.errors
            else str(list(form.errors.values())[0][0])
        ),
    }, 200
