# -*- coding: utf-8 -*-

from flask import Markup, escape, url_for

from baseframe import _, __
from lastuser_core.models import UserEmail, getuser
import baseframe.forms as forms


class LoginPasswordResetException(Exception):
    pass


class LoginForm(forms.Form):
    username = forms.StringField(
        __("Username or Email"),
        validators=[forms.validators.DataRequired()],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    password = forms.PasswordField(
        __("Password"), validators=[forms.validators.DataRequired()]
    )

    def validate_username(self, field):
        existing = getuser(field.data)
        if existing is None:
            raise forms.ValidationError(_("User does not exist"))

    def validate_password(self, field):
        if not self.username.data:
            # Can't validate password without a user
            return
        user = getuser(self.username.data)
        if user and not user.pw_hash:
            raise LoginPasswordResetException()
        if user is None or not user.password_is(field.data):
            if not self.username.errors:
                raise forms.ValidationError(_("Incorrect password"))
        self.user = user


class RegisterForm(forms.RecaptchaForm):
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
        __("Password"), validators=[forms.validators.DataRequired()]
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
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
                        "This email address is already registered. Do you want to <a href=\"{loginurl}\">login</a> instead?"
                    ).format(loginurl=escape(url_for('.login')))
                )
            )
