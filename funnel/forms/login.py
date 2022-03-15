from __future__ import annotations

from baseframe import _, __
import baseframe.forms as forms

from ..models import (
    PASSWORD_MAX_LENGTH,
    User,
    UserSession,
    check_password_strength,
    getuser,
)

__all__ = [
    'LoginPasswordResetException',
    'LoginPasswordWeakException',
    'LoginForm',
    'LogoutForm',
]


class LoginPasswordResetException(Exception):
    """Exception to signal that a password reset is required (not an error)."""


class LoginPasswordWeakException(Exception):
    """Exception to signal that password is weak and needs change (not an error)."""


@User.forms('login')
class LoginForm(forms.Form):
    __returns__ = ('user', 'weak_password')

    username = forms.StringField(
        __("Email, phone or username"),
        validators=[
            forms.validators.DataRequired(
                __("An email address, phone number or username is required")
            )
        ],
        filters=[forms.filters.strip()],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(__("Password is required")),
            forms.validators.Length(
                max=PASSWORD_MAX_LENGTH,
                message=__("Password must be under %(max)s characters"),
            ),
        ],
    )

    # These two validators depend on being called in sequence
    def validate_username(self, field):
        self.user = getuser(field.data)
        if self.user is None:
            raise forms.ValidationError(_("This user could not be identified"))

    def validate_password(self, field) -> None:
        # If there is already an error in the password field, don't bother validating.
        # This will be a `Length` validation error, but that one unfortunately does not
        # raise `StopValidation`, so we'll get called with potentially too much data
        if field.errors:
            return

        # Use `getattr` as `self.user` won't be set if the `DataRequired` validator
        # failed, as `validate_username` will not be called then
        if not getattr(self, 'user', None):
            # Can't validate password without a user. However, perform a safety check
            if not self.username.errors:  # pragma: no cover
                # This should never happen. Fields are validated in sequence, so
                # `username` must be validated before `password`, unless (a) someone
                # re-orders the fields, or (b) a future version of WTForms introduces
                # out-of-order processing (including single-field processing)
                raise ValueError("Password validated before username")
            # Username field has errors. We don't need to raise an error then
            return

        # If user does not have a password, ask for a password reset
        if not self.user.pw_hash:
            raise LoginPasswordResetException()

        # Check password. If valid but using a deprecated algorithm like bcrypt, also
        # perform an automatic hash upgrade
        if not self.user.password_is(field.data, upgrade_hash=True):
            raise forms.ValidationError(_("Incorrect password"))

        # Test for weak password. This gives us two options:
        #
        # 1. Flag it but allow login to proceed. Let the view ask the user nicely.
        #    The user may ignore it or may comply and change their password.
        #
        # 2. Block the login and force the user to reset their password. Makes for
        #    stronger policy, with the risk the user will (a) abandon the login, or
        #    (b) not have a valid email address on file (for example, an expired
        #    employer-owned email address they can no longer access).
        #
        # We're using option 1 here, but can switch to option 2 by raising
        # LoginPasswordWeakException after the test. The calling code in views/login.py
        # supports both outcomes.

        # check_password_strength(<password>)['is_weak'] returns True/False
        self.weak_password: bool = check_password_strength(field.data)['is_weak']


@User.forms('logout')
class LogoutForm(forms.Form):
    __expects__ = ('user',)
    __returns__ = ('user_session',)

    # Not HiddenField, because that gets rendered with hidden_tag, and not SubmitField
    # because that derives from BooleanField and will cast the value to a boolean
    sessionid = forms.StringField(
        __("Session id"), validators=[forms.validators.Optional()]
    )

    def validate_sessionid(self, field):
        user_session = UserSession.get(buid=field.data)
        if not user_session or user_session.user != self.user:
            raise forms.ValidationError(
                _("That does not appear to be a valid login session")
            )
        self.user_session = user_session
