from flask import Markup, escape, url_for

from baseframe import _, __
import baseframe.forms as forms

from ..models import User, UserEmail, getuser
from .account import password_policy, password_strength_validator

__all__ = [
    'LoginPasswordResetException',
    'LoginPasswordWeakException',
    'LoginForm',
    'RegisterForm',
]


class LoginPasswordResetException(Exception):
    pass


class LoginPasswordWeakException(Exception):
    pass


@User.forms('login')
class LoginForm(forms.Form):
    __returns__ = ('user', 'weak_password')

    username = forms.StringField(
        __("Username or Email"),
        validators=[forms.validators.DataRequired()],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    password = forms.PasswordField(
        __("Password"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=40)],
    )

    # These two validators depend on being called in sequence
    def validate_username(self, field):
        self.user = getuser(field.data)
        if self.user is None:
            raise forms.ValidationError(_("User does not exist"))

    def validate_password(self, field):
        if not self.user:
            # Can't validate password without a user
            return
        if not self.user.pw_hash:
            raise LoginPasswordResetException()
        if not self.user.password_is(field.data, upgrade_hash=True):
            if not self.username.errors:
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

        # password_policy.test returns [] if no issues were found
        self.weak_password = bool(password_policy.test(field.data))


@User.forms('register')
class RegisterForm(forms.RecaptchaForm):
    __returns__ = ('password_strength',)  # Set by password_strength_validator

    fullname = forms.StringField(
        __("Full name"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
    )
    email = forms.EmailField(
        __("Email address"),
        validators=[forms.validators.DataRequired(), forms.validators.ValidEmail()],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=8, max=40),
            password_strength_validator,
        ],
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=8, max=40),
            forms.validators.EqualTo('password'),
        ],
    )

    def validate_email(self, field):
        field.data = field.data.lower()  # Convert to lowercase
        existing = UserEmail.get(email=field.data)
        if existing is not None:
            raise forms.ValidationError(
                Markup(
                    _(
                        'This email address is already registered. '
                        'Do you want to <a href="{loginurl}">login</a> instead?'
                    ).format(loginurl=escape(url_for('login')))
                )
            )
