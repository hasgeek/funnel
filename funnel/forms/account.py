from __future__ import annotations

import phonenumbers

from baseframe import _, __
from coaster.auth import current_auth
from coaster.utils import sorted_timezones
import baseframe.forms as forms

from ..models import (
    MODERATOR_REPORT_TYPE,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    Profile,
    User,
    UserEmailClaim,
    UserPhone,
    UserPhoneClaim,
    check_password_strength,
    getuser,
)
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
    'VerifyEmailForm',
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
    default_message = _(
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
class RegisterForm(forms.RecaptchaForm):
    __returns__ = ('password_strength',)  # Set by PasswordStrengthValidator

    fullname = forms.StringField(
        __("Full name"),
        description=__(
            "This account is for you as an individual. We’ll make one for your organization later"
        ),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        filters=[forms.filters.strip()],
    )
    email = forms.EmailField(
        __("Email address"),
        validators=[
            forms.validators.DataRequired(),
            EmailAddressAvailable(purpose='register'),
        ],
        filters=strip_filters,
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(user_input_fields=['fullname', 'email']),
        ],
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
    )


@User.forms('password')
class PasswordForm(forms.Form):
    __expects__ = ('edit_user',)

    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=PASSWORD_MAX_LENGTH),
        ],
    )

    def validate_password(self, field):
        if not self.edit_user.password_is(field.data):
            raise forms.ValidationError(_("Incorrect password"))


@User.forms('password_policy')
class PasswordPolicyForm(forms.Form):
    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=PASSWORD_MAX_LENGTH),
        ],
    )


@User.forms('password_reset_request')
class PasswordResetRequestForm(forms.RecaptchaForm):
    username = forms.StringField(
        __("Username or Email"),
        validators=[forms.validators.DataRequired()],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )

    def validate_username(self, field):
        user = getuser(field.data)
        if user is None:
            raise forms.ValidationError(_("Could not find a user with that id"))
        self.user = user


@User.forms('password_create')
class PasswordCreateForm(forms.Form):
    __returns__ = ('password_strength',)
    __expects__ = ('edit_user',)

    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(),
        ],
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
    )


@User.forms('password_reset')
class PasswordResetForm(forms.RecaptchaForm):
    __returns__ = ('password_strength',)

    username = forms.StringField(
        __("Username or Email"),
        validators=[forms.validators.DataRequired()],
        description=__("Please reconfirm your username or email address"),
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )

    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(user_input_fields=['username']),
        ],
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
    )

    def validate_username(self, field):
        user = getuser(field.data)
        if user is None or user != self.edit_user:
            raise forms.ValidationError(
                _(
                    "This username or email does not match the user the reset code is"
                    " for"
                )
            )


@User.forms('password_change')
class PasswordChangeForm(forms.Form):
    __returns__ = ('password_strength',)
    __expects__ = ('edit_user',)

    old_password = forms.PasswordField(
        __("Current password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=PASSWORD_MAX_LENGTH),
        ],
    )
    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(),
        ],
    )
    confirm_password = forms.PasswordField(
        __("Confirm password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            forms.validators.EqualTo('password'),
        ],
    )

    def validate_old_password(self, field):
        if self.edit_user is None:
            raise forms.ValidationError(_("Not logged in"))
        if not self.edit_user.password_is(field.data):
            raise forms.ValidationError(_("Incorrect password"))


def raise_username_error(reason):
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
    )
    email = forms.EmailField(
        __("Email address"),
        description=__("Required for sending you tickets, invoices and notifications"),
        validators=[
            forms.validators.DataRequired(),
            EmailAddressAvailable(purpose='use'),
        ],
        filters=strip_filters,
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
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
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    timezone = forms.SelectField(
        __("Timezone"),
        description=__(
            "Where in the world are you? Dates and times will be shown in your local"
            " timezone"
        ),
        validators=[forms.validators.DataRequired()],
        choices=timezones,
        widget_attrs={},
    )
    auto_timezone = forms.BooleanField(__("Use your device’s timezone"))
    locale = forms.SelectField(
        __("Locale"),
        description=__("Your preferred UI language"),
        choices=list(supported_locales.items()),
    )
    auto_locale = forms.BooleanField(__("Use your device’s language"))

    def validate_username(self, field):
        reason = self.edit_obj.validate_name_candidate(field.data)
        if not reason:
            return  # Username is available
        raise_username_error(reason)


class UsernameAvailableForm(forms.Form):
    __expects__ = ('edit_user',)

    username = forms.StringField(
        __("Username"),
        validators=[forms.validators.DataRequired(__("This is required"))],
        filters=[forms.filters.strip()],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )

    def validate_username(self, field):
        if self.edit_user:  # User is setting a username
            reason = self.edit_user.validate_name_candidate(field.data)
        else:  # New user is creating an account, so no user object yet
            reason = Profile.validate_name_candidate(field.data)
        if not reason:
            return  # Username is available
        raise_username_error(reason)


def validate_emailclaim(form, field):
    existing = UserEmailClaim.get_for(user=current_auth.user, email=field.data)
    if existing is not None:
        raise forms.StopValidation(_("This email address is pending verification"))


@User.forms('email_add')
class NewEmailAddressForm(forms.RecaptchaForm):
    email = forms.EmailField(
        __("Email address"),
        validators=[
            forms.validators.DataRequired(),
            validate_emailclaim,
            EmailAddressAvailable(purpose='claim'),
        ],
        filters=strip_filters,
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    type = forms.RadioField(
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
    email = forms.EmailField(
        __("Email address"),
        validators=[forms.validators.DataRequired()],
        filters=strip_filters,
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )


@User.forms('email_verify')
class VerifyEmailForm(forms.Form):
    pass


@User.forms('phone_add')
class NewPhoneForm(forms.RecaptchaForm):
    phone = forms.TelField(
        __("Phone number"),
        validators=[forms.validators.DataRequired()],
        filters=strip_filters,
        description=__("Mobile numbers only, in Indian or international format"),
    )

    # Temporarily removed since we only support mobile numbers at this time. When phone
    # call validation is added, we can ask for other types of numbers:

    # type = forms.RadioField(__("Type"),
    #     validators=[forms.validators.Optional()],
    #     filters=strip_filters,
    #     choices=[
    #         (__("Mobile"), __("Mobile")),
    #         (__("Home"), __("Home")),
    #         (__("Work"), __("Work")),
    #         (__("Other"), __("Other"))])

    enable_notifications = forms.BooleanField(
        __("Send notifications by SMS"),
        description=__(
            "Unsubscribe anytime, and control what notifications are sent from the"
            " Notifications tab under account settings"
        ),
        default=True,
    )

    def validate_phone(self, field):
        # Step 1: Validate number
        try:
            # Assume Indian number if no country code is specified
            # TODO: Guess country from IP address
            parsed_number = phonenumbers.parse(field.data, 'IN')
            if not phonenumbers.is_valid_number(parsed_number):
                raise ValueError("Invalid number")
        except (phonenumbers.NumberParseException, ValueError):
            raise forms.StopValidation(
                _("This does not appear to be a valid phone number")
            )
        number = phonenumbers.format_number(
            parsed_number, phonenumbers.PhoneNumberFormat.E164
        )
        # Step 2: Check if number has already been claimed
        existing = UserPhone.get(phone=number)
        if existing is not None:
            if existing.user == current_auth.user:
                raise forms.ValidationError(
                    _("You have already registered this phone number")
                )
            else:
                raise forms.ValidationError(
                    _("This phone number has already been claimed")
                )
        existing = UserPhoneClaim.get_for(user=current_auth.user, phone=number)
        if existing is not None:
            raise forms.ValidationError(_("This phone number is pending verification"))
        # Step 3: If validations pass, use the reformatted number
        field.data = number  # Save stripped number


@User.forms('phone_primary')
class PhonePrimaryForm(forms.Form):
    phone = forms.StringField(
        __("Phone number"),
        validators=[forms.validators.DataRequired()],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )


@User.forms('phone_verify')
class VerifyPhoneForm(forms.Form):
    verification_code = forms.StringField(
        __("Verification code"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
        widget_attrs={'pattern': '[0-9]*', 'autocomplete': 'off'},
    )

    def validate_verification_code(self, field):
        # self.phoneclaim is set by the view before calling form.validate()
        if self.phoneclaim.verification_code != field.data:
            raise forms.ValidationError(_("Verification code does not match"))


class ModeratorReportForm(forms.Form):
    report_type = forms.SelectField(
        __("Report type"), coerce=int, validators=[forms.validators.InputRequired()]
    )

    def set_queries(self):
        self.report_type.choices = [
            (idx, report_type.title)
            for idx, report_type in MODERATOR_REPORT_TYPE.items()
        ]
