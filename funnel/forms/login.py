"""Forms for login and logout."""

from __future__ import annotations

from typing import TYPE_CHECKING

from baseframe import _, __, forms

from ..models import (
    PASSWORD_MAX_LENGTH,
    Account,
    AccountEmail,
    AccountEmailClaim,
    AccountPhone,
    EmailAddress,
    EmailAddressBlockedError,
    LoginSession,
    PhoneNumber,
    PhoneNumberBlockedError,
    User,
    check_password_strength,
    getuser,
    parse_phone_number,
)
from .helpers import (
    MSG_EMAIL_BLOCKED,
    MSG_EMAIL_INVALID,
    MSG_INCORRECT_OTP,
    MSG_INCORRECT_PASSWORD,
    MSG_NO_ACCOUNT,
    MSG_NO_LOGIN_SESSION,
    MSG_PHONE_BLOCKED,
    MSG_PHONE_NO_SMS,
)

__all__ = [
    'LoginPasswordResetException',
    'LoginPasswordWeakException',
    'LoginWithOtp',
    'LoginForm',
    'LogoutForm',
    'RegisterWithOtp',
    'OtpForm',
    'EmailOtpForm',
    'RegisterOtpForm',
]


# --- Exceptions -----------------------------------------------------------------------


class LoginPasswordResetException(Exception):  # noqa: N818
    """Exception to signal that a password reset is required (not an error)."""


class LoginPasswordWeakException(Exception):  # noqa: N818
    """Exception to signal that password is weak and needs change (not an error)."""


class LoginWithOtp(Exception):  # noqa: N818
    """Exception to signal that login may proceed using an OTP instead of password."""


class RegisterWithOtp(Exception):  # noqa: N818
    """Exception to signal for new account registration after OTP validation."""


# --- Validators -----------------------------------------------------------------------


# Validator specifically for LoginForm
class PasswordlessLoginIntercept:
    """Allow password to be optional if an anchor (phone, email) is available."""

    message = __("Password is required")

    def __call__(self, form, field) -> None:
        if not field.data:
            # Use getattr for when :meth:`LoginForm.validate_username` is skipped
            if getattr(form, 'anchor', None) is not None:
                # If user has an anchor, we can allow login to proceed passwordless
                # using an OTP or email link
                raise LoginWithOtp()
            if (
                getattr(form, 'new_email', None) is not None
                or getattr(form, 'new_phone', None) is not None
            ):
                raise RegisterWithOtp()
            if form.username.errors:
                # Since username field had errors, we don't need to ask for a password
                raise forms.validators.StopValidation()
            raise forms.validators.StopValidation(self.message)


# --- Forms ----------------------------------------------------------------------------


@Account.forms('login')
class LoginForm(forms.RecaptchaForm):
    """
    Form for login and registration.

    Login is accepted via password or OTP. If password is blank, OTP flow is assumed and
    the view is expected to continue using the separate
    :class:`~funnel.forms.account.OtpForm`.

    In case a matching user account cannot be found and a password is not provided, the
    username is validated to be an email address or phone number, and flow is expected
    to continue using the separate :class:`~funnel.forms.account.RegisterOtpForm`.

    This form signals these special cases by raising specific exceptions for each
    scenario.

    :raises LoginWithOtp: Valid account with a valid anchor (email or phone) and
        password is not provided, so OTP flow is required
    :raises RegisterWithOtp: No such account, but a syntactically valid email address or
        phone number was provided, so OTP flow is required for user registration
    :raises LoginPasswordResetException: A password was provided but the user does not
        have a password, so they must be sent a reset link or OTP
    :raises LoginPasswordWeakException: Backup exception for signalling a weak password,
        currently not used. The form instead sets ``form.weak_password`` to `True`
    """

    __returns__ = ('user', 'anchor', 'weak_password', 'new_email', 'new_phone')
    user: Account | None = None
    anchor: AccountEmail | AccountEmailClaim | AccountPhone | None = None
    weak_password: bool | None = None
    new_email: str | None = None
    new_phone: str | None = None

    username = forms.StringField(
        __("Phone number or email address"),
        validators=[
            forms.validators.DataRequired(
                __("A phone number or email address is required")
            )
        ],
        filters=[forms.filters.strip()],
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'username',
            'inputmode': 'email',
        },
    )
    password = forms.PasswordField(
        __("Password"),
        validators=[
            PasswordlessLoginIntercept(),
            forms.validators.Length(
                max=PASSWORD_MAX_LENGTH,
                message=__("Password must be under %(max)s characters"),
            ),
        ],
        render_kw={'autocomplete': 'current-password'},
    )

    # These two validators depend on being called in sequence
    def validate_username(self, field: forms.Field) -> None:
        """Process username field and load user and anchor."""
        self.user, self.anchor = getuser(field.data, True)  # skipcq: PYL-W0201
        self.new_email = self.new_phone = None
        if self.user is None:
            # This is not a known user. Assume it's a new account registration and
            # attempt to process as a new email address or phone number.
            if '@' in field.data:
                # Looks like email, try to process
                try:
                    # Since we are going to send an OTP, we must add the email address
                    # to the database
                    email_address = EmailAddress.add(field.data)
                    # This gets us a normalized email address
                    self.new_email = str(email_address)
                except EmailAddressBlockedError as exc:
                    raise forms.validators.ValidationError(MSG_EMAIL_BLOCKED) from exc
                except ValueError as exc:
                    raise forms.validators.StopValidation(MSG_EMAIL_INVALID) from exc
                return
            phone = parse_phone_number(field.data, sms=True)
            if phone is False:
                raise forms.validators.ValidationError(MSG_PHONE_NO_SMS)
            if phone is not None:
                try:
                    # Since we are going to send an OTP, we must add the phone number
                    # to the database
                    phone_number = PhoneNumber.add(phone)
                except PhoneNumberBlockedError as exc:
                    raise forms.validators.ValidationError(MSG_PHONE_BLOCKED) from exc
                self.new_phone = str(phone_number)
                return
            # Not a known user and not a valid email address or phone number -> error
            raise forms.validators.ValidationError(MSG_NO_ACCOUNT)

    def validate_password(self, field: forms.Field) -> None:
        """Validate password if provided."""
        # If there is already an error in the password field, don't bother validating.
        # This will be a `Length` validation error, but that one unfortunately does not
        # raise `StopValidation`. If the length is off, we can end rightaway.
        if field.errors:
            return

        # We use `getattr` here as `self.user` won't be set if the `DataRequired`
        # validator failed on the `user` field, thereby blocking the call to
        # `validate_username`
        if getattr(self, 'user', None) is None:
            if self.username.errors:
                # Username field has errors. We don't need to raise an error then
                return
            # There is no matching user account, but since the user is attempting a
            # password login, we tell them the password is incorrect. This avoids
            # revealing a nonexistent account. Note that OTP flow will identify a
            # non-existent account through the use of `RegisterOtpForm` instead of
            # `OtpForm`, but it will also notify the target by sending them an OTP
            raise forms.validators.ValidationError(MSG_INCORRECT_PASSWORD)

        # From here on `self.user` is guaranteed to be a `User` instance, but mypy
        # can't infer and must be told
        if TYPE_CHECKING:
            assert isinstance(self.user, User)  # nosec

        # If user does not have a password, ask for a password reset. Since
        # :class:`PasswordlessLoginIntercept` already intercepts for a blank password,
        # we will only get here if an invalid password was provided in the form
        if not self.user.pw_hash:
            raise LoginPasswordResetException()

        # Check password. If valid but using a deprecated algorithm like bcrypt, also
        # perform an automatic hash upgrade
        if not self.user.password_is(field.data, upgrade_hash=True):
            raise forms.validators.ValidationError(MSG_INCORRECT_PASSWORD)

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

        # `check_password_strength(password).is_weak` is a bool
        self.weak_password: bool = check_password_strength(field.data).is_weak


@Account.forms('logout')
class LogoutForm(forms.Form):
    """Process a logout request."""

    __expects__ = ('user',)
    __returns__ = ('login_session',)
    user: Account
    login_session: LoginSession | None = None

    # We use `StringField`` even though the field is not visible. This does not use
    # `HiddenField`, because that gets rendered with `hidden_tag`, and not `SubmitField`
    # because that derives from `BooleanField` and will cast the value to a boolean
    sessionid = forms.StringField(
        __("Session id"), validators=[forms.validators.Optional()]
    )

    def validate_sessionid(self, field: forms.Field) -> None:
        """Validate login session belongs to the user who invoked this form."""
        login_session = LoginSession.get(buid=field.data)
        if not login_session or login_session.account != self.user:
            raise forms.validators.ValidationError(MSG_NO_LOGIN_SESSION)
        self.login_session = login_session


class OtpForm(forms.Form):
    """Verify an OTP."""

    __expects__ = ('valid_otp',)
    valid_otp: str

    otp = forms.StringField(
        __("OTP"),
        description=__("One-time password sent to your device"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
        render_kw={
            'pattern': '[0-9]*',
            'autocomplete': 'one-time-code',
            'autocorrect': 'off',
            'inputmode': 'numeric',
        },
    )

    def validate_otp(self, field: forms.Field) -> None:
        """Confirm OTP is as expected."""
        if field.data != self.valid_otp:
            raise forms.validators.StopValidation(MSG_INCORRECT_OTP)


class EmailOtpForm(OtpForm):
    """Verify an OTP sent to email."""

    def set_queries(self) -> None:
        super().set_queries()
        self.otp.description = _("One-time password sent to your email address")


class RegisterOtpForm(forms.Form):
    """Verify an OTP and register an account."""

    __expects__ = ('valid_otp',)
    valid_otp: str

    fullname = forms.StringField(
        __("Your name"),
        description=__(
            "This account is for you as an individual. We’ll make one for your"
            " organization later"
        ),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
        render_kw={'autocomplete': 'name'},
    )

    otp = forms.StringField(
        __("OTP"),
        description=__("One-time password sent to your device"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
        render_kw={
            'pattern': '[0-9]*',
            'autocomplete': 'one-time-code',
            'autocorrect': 'off',
            'inputmode': 'numeric',
        },
    )

    def validate_otp(self, field: forms.Field) -> None:
        """Confirm OTP is as expected."""
        if field.data != self.valid_otp:
            raise forms.validators.StopValidation(MSG_INCORRECT_OTP)
