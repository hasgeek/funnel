from baseframe import _, __
import baseframe.forms as forms

from ..models import User, UserSession, getuser
from .account import password_policy

__all__ = [
    'LoginPasswordResetException',
    'LoginPasswordWeakException',
    'LoginForm',
    'LogoutForm',
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

        # password_policy.test_password(<password>)['is_weak'] returns True/False
        self.weak_password = password_policy.test_password(field.data)['is_weak']


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
