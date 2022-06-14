"""Forms for user account settings."""

from __future__ import annotations

from typing import Optional

from baseframe import _, __, forms
from coaster.utils import sorted_timezones

from ..models import (
    MODERATOR_REPORT_TYPE,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    Anchor,
    Profile,
    User,
    UserEmailClaim,
    UserPhone,
    UserPhoneClaim,
    check_password_strength,
    getuser,
)
from ..utils import normalize_phone_number
from .helpers import EmailAddressAvailable, strip_filters

__all__ = [
    'RegisterForm',
    'PasswordForm',
    'PasswordCreateForm',
    'PasswordPolicyForm',
    'PasswordResetRequestForm',
    'PasswordResetForm',
    'PasswordChangeForm',
    'AccountForm',
    'UsernameAvailableForm',
    'EmailPrimaryForm',
    'ModeratorReportForm',
    'NewEmailAddressForm',
    'NewPhoneForm',
    'PhonePrimaryForm',
    'VerifyPhoneForm',
    'supported_locales',
    'timezone_identifiers',
]


timezones = sorted_timezones()
timezone_identifiers = dict(timezones)

supported_locales = {
    'en': __("English"),
    'hi': __("Hindi (beta; incomplete)"),
}


class PasswordStrengthValidator:
    """Validate password strength (reused across forms)."""

    default_message = __(
        "This password is too simple. Add complexity by making it longer and using"
        " a mix of upper and lower case letters, numbers and symbols"
    )

    def __init__(self, user_input_fields=(), message=None) -> None:
        self.user_input_fields = user_input_fields
        self.message = message or self.default_message

    def __call__(self, form, field):
        user_inputs = []
        for field_name in self.user_input_fields:
            user_inputs.append(getattr(form, field_name).data)

        if hasattr(form, 'edit_user') and form.edit_user is not None:
            if form.edit_user.username:
                user_inputs.append(form.edit_user.username)
            if form.edit_user.fullname:
                user_inputs.append(form.edit_user.fullname)

            for useremail in form.edit_user.emails:
                user_inputs.append(str(useremail))
            for emailclaim in form.edit_user.emailclaims:
                user_inputs.append(str(emailclaim))

            for userphone in form.edit_user.phones:
                user_inputs.append(str(userphone))
            for phoneclaim in form.edit_user.phoneclaims:
                user_inputs.append(str(phoneclaim))

        tested_password = check_password_strength(
            field.data, user_inputs=user_inputs if user_inputs else None
        )
        # Stick password strength into the form for logging in the view and possibly
        # rendering into UI
        form.password_strength = float(tested_password['score'])
        # No test failures? All good then
        if not tested_password['is_weak']:
            return
        # Tell the user to make up a better password
        raise forms.validators.StopValidation(
            tested_password['warning']
            if tested_password['warning']
            else '\n'.join(tested_password['suggestions'])
            if tested_password['suggestions']
            else self.message
        )


@User.forms('register')
class RegisterForm(forms.Form):
    """
    Traditional account registration form.

    This form has been deprecated by the combination of
    :class:`~funnel.forms.login.LoginForm` and :class:`~funnel.forms.RegisterOtpForm`
    for most users. Users who cannot receive an OTP (unsupported country for phone)
    will continue to use password-based registration.
    """

    __returns__ = ('password_strength',)  # Set by PasswordStrengthValidator
    password_strength: Optional[float] = None

    fullname = forms.StringField(
        __("Full name"),
        description=__(
            "This account is for you as an individual. We’ll make one for your"
            " organization later"
        ),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
        render_kw={'autocomplete': 'name'},
    )
    email = forms.EmailField(
        __("Email address"),
        validators=[
            forms.validators.DataRequired(),
            EmailAddressAvailable(purpose='register'),
        ],
        filters=strip_filters,
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'email',
        },
    )
    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(user_input_fields=['fullname', 'email']),
        ],
        render_kw={'autocomplete': 'new-password'},
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
        render_kw={'autocomplete': 'new-password'},
    )


@User.forms('password')
class PasswordForm(forms.Form):
    """Form to validate a user's password, for password-gated sudo actions."""

    __expects__ = ('edit_user',)
    edit_user: User

    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=PASSWORD_MAX_LENGTH),
        ],
        render_kw={'autocomplete': 'current-password'},
    )

    def validate_password(self, field):
        """Check for password match."""
        if not self.edit_user.password_is(field.data):
            raise forms.ValidationError(_("Incorrect password"))


@User.forms('password_policy')
class PasswordPolicyForm(forms.Form):
    """Form to validate any candidate password against policy."""

    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=PASSWORD_MAX_LENGTH),
        ],
    )


@User.forms('password_reset_request')
class PasswordResetRequestForm(forms.Form):
    """Form to request a password reset."""

    __returns__ = ('user', 'anchor')
    user: Optional[User] = None
    anchor: Optional[Anchor] = None

    username = forms.StringField(
        __("Phone number or email address"),
        validators=[forms.validators.DataRequired()],
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
        },
    )

    def validate_username(self, field):
        """Process username to retrieve user."""
        self.user, self.anchor = getuser(field.data, True)
        if self.user is None:
            raise forms.ValidationError(_("Could not find a user with that id"))


@User.forms('password_create')
class PasswordCreateForm(forms.Form):
    """Form to accept a new password for a given user, without existing password."""

    __returns__ = ('password_strength',)
    __expects__ = ('edit_user',)
    edit_user: User
    password_strength: Optional[float] = None

    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(),
        ],
        render_kw={'autocomplete': 'new-password'},
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
        render_kw={'autocomplete': 'new-password'},
    )


@User.forms('password_reset')
class PasswordResetForm(forms.Form):
    """Form to reset a password for a user, requiring the user id as a failsafe."""

    __returns__ = ('password_strength',)
    password_strength: Optional[float] = None

    # TODO: This form has been deprecated with OTP-based reset as that doesn't need
    # username and now uses :class:`PasswordCreateForm`. This form is retained in the
    # interim in case email link-based flow is reintroduced. It should be removed
    # after a waiting period (as of May 2022).

    username = forms.StringField(
        __("Phone number or email address"),
        validators=[forms.validators.DataRequired()],
        description=__("Please reconfirm your phone number, email address or username"),
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'username',
        },
    )

    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(),
        ],
        render_kw={'autocomplete': 'new-password'},
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
        render_kw={'autocomplete': 'new-password'},
    )

    def validate_username(self, field):
        """Confirm the user provided by the client is who this form is meant for."""
        user = getuser(field.data)
        if user is None or user != self.edit_user:
            raise forms.ValidationError(
                _("This does not match the user the reset code is for")
            )


@User.forms('password_change')
class PasswordChangeForm(forms.Form):
    """Form to change a user's password after confirming the old password."""

    __returns__ = ('password_strength',)
    __expects__ = ('edit_user',)
    edit_user: User
    password_strength: Optional[float] = None

    old_password = forms.PasswordField(
        __("Current password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=PASSWORD_MAX_LENGTH),
        ],
        render_kw={'autocomplete': 'current-password'},
    )
    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(),
        ],
        render_kw={'autocomplete': 'new-password'},
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
        render_kw={'autocomplete': 'new-password'},
    )

    def validate_old_password(self, field):
        """Validate the old password to be correct."""
        if self.edit_user is None:
            raise forms.ValidationError(_("Not logged in"))
        if not self.edit_user.password_is(field.data):
            raise forms.ValidationError(_("Incorrect password"))


def raise_username_error(reason: str) -> str:
    """Provide a user-friendly error message for a username field error."""
    if reason == 'blank':
        raise forms.ValidationError(_("This is required"))
    if reason == 'long':
        raise forms.ValidationError(_("This is too long"))
    if reason == 'invalid':
        raise forms.ValidationError(
            _(
                "Usernames can only have alphabets, numbers and dashes (except at the"
                " ends)"
            )
        )
    if reason == 'reserved':
        raise forms.ValidationError(_("This username is reserved"))
    if reason in ('user', 'org'):
        raise forms.ValidationError(_("This username has been taken"))
    raise forms.ValidationError(_("This username is not available"))


@User.forms('main')
class AccountForm(forms.Form):
    """Form to edit basic account details."""

    fullname = forms.StringField(
        __("Full name"),
        description=__(
            "This is your name. We will make an account for your organization later"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=User.__title_length__),
        ],
        filters=[forms.filters.strip()],
        render_kw={'autocomplete': 'name'},
    )
    email = forms.EmailField(
        __("Email address"),
        description=__("Required for sending you tickets, invoices and notifications"),
        validators=[
            forms.validators.DataRequired(),
            EmailAddressAvailable(purpose='use'),
        ],
        filters=strip_filters,
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'email',
        },
    )
    username = forms.AnnotatedTextField(
        __("Username"),
        description=__(
            "Single word that can contain letters, numbers and dashes."
            " You need a username to have a public profile"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Profile.__name_length__),
        ],
        filters=[forms.filters.none_if_empty()],
        prefix="https://hasgeek.com/",
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
        },
    )
    timezone = forms.SelectField(
        __("Timezone"),
        description=__(
            "Where in the world are you? Dates and times will be shown in your local"
            " timezone"
        ),
        validators=[forms.validators.DataRequired()],
        choices=timezones,
        render_kw={},
    )
    auto_timezone = forms.BooleanField(__("Use your device’s timezone"))
    locale = forms.SelectField(
        __("Locale"),
        description=__("Your preferred UI language"),
        choices=list(supported_locales.items()),
    )
    auto_locale = forms.BooleanField(__("Use your device’s language"))

    def validate_username(self, field):
        """Validate if username is appropriately formatted and available to use."""
        reason = self.edit_obj.validate_name_candidate(field.data)
        if not reason:
            return  # Username is available
        raise_username_error(reason)


class UsernameAvailableForm(forms.Form):
    """Form to check for whether a username is available to use."""

    __expects__ = ('edit_user',)
    edit_user: User

    username = forms.StringField(
        __("Username"),
        validators=[forms.validators.DataRequired(__("This is required"))],
        filters=[forms.filters.strip()],
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
        },
    )

    def validate_username(self, field):
        """Validate for username being valid and available (with optionally user)."""
        if self.edit_user:  # User is setting a username
            reason = self.edit_user.validate_name_candidate(field.data)
        else:  # New user is creating an account, so no user object yet
            reason = Profile.validate_name_candidate(field.data)
        if not reason:
            return  # Username is available
        raise_username_error(reason)


def validate_emailclaim(form, field):
    """Validate if an email address is already pending verification."""
    existing = UserEmailClaim.get_for(user=form.edit_user, email=field.data)
    if existing is not None:
        raise forms.StopValidation(_("This email address is pending verification"))


@User.forms('email_add')
class NewEmailAddressForm(forms.Form):
    """Form to add a new email address to a user account."""

    __expects__ = ('edit_user',)
    edit_user: User

    email = forms.EmailField(
        __("Email address"),
        validators=[
            forms.validators.DataRequired(),
            validate_emailclaim,
            EmailAddressAvailable(purpose='claim'),
        ],
        filters=strip_filters,
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'email',
        },
    )
    type = forms.RadioField(  # noqa: A003
        __("Type"),
        validators=[forms.validators.Optional()],
        filters=[forms.filters.strip()],
        choices=[
            (__("Home"), __("Home")),
            (__("Work"), __("Work")),
            (__("Other"), __("Other")),
        ],
    )


@User.forms('email_primary')
class EmailPrimaryForm(forms.Form):
    """Form to mark an email address as a user's primary."""

    email = forms.EmailField(
        __("Email address"),
        validators=[forms.validators.DataRequired()],
        filters=strip_filters,
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'email',
        },
    )


@User.forms('phone_add')
class NewPhoneForm(forms.Form):
    """Form to add a new mobile number (SMS-capable) to a user account."""

    __expects__ = ('edit_user',)
    edit_user: User

    phone = forms.TelField(
        __("Phone number"),
        validators=[forms.validators.DataRequired()],
        filters=strip_filters,
        description=__("Mobile numbers only, in Indian or international format"),
        render_kw={'autocomplete': 'tel'},
    )

    enable_notifications = forms.BooleanField(
        __("Send notifications by SMS"),
        description=__(
            "Unsubscribe anytime, and control what notifications are sent from the"
            " Notifications tab under account settings"
        ),
        default=True,
    )

    def validate_phone(self, field):
        """Validate a phone number to be a mobile number and to be available."""
        # Step 1: Validate number
        number = normalize_phone_number(field.data, sms=True)
        if number is False:
            raise forms.StopValidation(
                _("This phone number cannot receive SMS messages")
            )
        if not number:
            raise forms.StopValidation(
                _("This does not appear to be a valid phone number")
            )
        # Step 2: Check if number has already been claimed
        existing = UserPhone.get(phone=number)
        if existing is not None:
            if existing.user == self.edit_user:
                raise forms.ValidationError(
                    _("You have already registered this phone number")
                )
            raise forms.ValidationError(_("This phone number has already been claimed"))
        existing = UserPhoneClaim.get_for(user=self.edit_user, phone=number)
        if existing is not None:
            raise forms.ValidationError(_("This phone number is pending verification"))
        # Step 3: If validations pass, use the reformatted number
        field.data = number  # Save stripped number


@User.forms('phone_primary')
class PhonePrimaryForm(forms.Form):
    """Form to mark a phone number as a user's primary."""

    phone = forms.StringField(
        __("Phone number"),
        validators=[forms.validators.DataRequired()],
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'tel',
        },
    )


@User.forms('phone_verify')
class VerifyPhoneForm(forms.Form):
    """Verify a phone number with an OTP (TODO: pending deprecation with OtpForm)."""

    verification_code = forms.StringField(
        __("Verification code"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
        render_kw={
            'pattern': '[0-9]*',
            'autocomplete': 'one-time-code',
            'autocorrect': 'off',
            'inputmode': 'numeric',
        },
    )

    def validate_verification_code(self, field):
        """Validate verification code provided by user matches what is expected."""
        # self.phoneclaim is set by the view before calling form.validate()
        if self.phoneclaim.verification_code != field.data:
            raise forms.ValidationError(_("Verification code does not match"))


class ModeratorReportForm(forms.Form):
    """Form to accept a comment moderator's report (spam or not spam)."""

    report_type = forms.SelectField(
        __("Report type"), coerce=int, validators=[forms.validators.InputRequired()]
    )

    def set_queries(self):
        """Prepare form for use."""
        self.report_type.choices = [
            (idx, report_type.title)
            for idx, report_type in MODERATOR_REPORT_TYPE.items()
        ]
