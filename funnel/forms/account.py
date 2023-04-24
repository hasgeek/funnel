"""Forms for user account settings."""

from __future__ import annotations

from hashlib import sha1
from typing import Dict, Iterable, Optional

from flask_babel import ngettext

import requests

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
    check_password_strength,
    getuser,
)
from .helpers import (
    EmailAddressAvailable,
    PhoneNumberAvailable,
    nullable_strip_filters,
    strip_filters,
)

__all__ = [
    'PasswordForm',
    'PasswordCreateForm',
    'PasswordPolicyForm',
    'PasswordResetRequestForm',
    'PasswordResetForm',
    'PasswordChangeForm',
    'AccountForm',
    'AccountDeleteForm',
    'UsernameAvailableForm',
    'EmailPrimaryForm',
    'ModeratorReportForm',
    'NewEmailAddressForm',
    'NewPhoneForm',
    'PhonePrimaryForm',
    'supported_locales',
    'timezone_identifiers',
    'pwned_password_validator',
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

    def __call__(self, form, field) -> None:
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

        tested_password = check_password_strength(
            field.data, user_inputs=user_inputs if user_inputs else None
        )
        # Stick password strength into the form for logging in the view and possibly
        # rendering into UI
        form.password_strength = tested_password.score
        # No test failures? All good then
        if not tested_password.is_weak:
            return
        # Tell the user to make up a better password
        raise forms.validators.StopValidation(
            tested_password.warning
            if tested_password.warning
            else '\n'.join(tested_password.suggestions)
            if tested_password.suggestions
            else self.message
        )


def pwned_password_validator(_form, field) -> None:
    """Validate password against the pwned password API."""
    # Add usedforsecurity=False when migrating to Python 3.9+
    phash = sha1(field.data.encode()).hexdigest().upper()  # nosec
    prefix, suffix = phash[:5], phash[5:]

    try:
        rv = requests.get(f'https://api.pwnedpasswords.com/range/{prefix}', timeout=10)
        if rv.status_code != 200:
            # API call had an error and we can't proceed with validation.
            return
        # This API returns minimal plaintext containing ``suffix:count``, one per line.
        # The following code is defensive, attempting to add mitigations (inner->outer):
        # 1. If there's no : separator, assume a count of 1
        # 2. Strip text on either side of the colon
        # 3. Ensure the suffix is uppercase
        # 4. If count is not a number, default it to 0 (ie, this is not a match)
        matches: Dict[str, int] = {
            line_suffix.upper(): int(line_count) if line_count.isdigit() else 0
            for line_suffix, line_count in (
                (split1.strip(), split2.strip())
                for split1, split2 in (
                    (line + (':1' if ':' not in line else '')).split(':', 1)
                    for line in rv.text.splitlines()
                )
            )
        }
    except requests.RequestException:
        # An exception occurred and we have no data to validate password against
        return

    # If we have data, check for our hash suffix in the returned range of matches
    count = matches.get(suffix, None)
    if count:  # not 0 and not None
        raise forms.validators.StopValidation(
            ngettext(
                "This password was found in a breached password list and is not safe to"
                " use",
                "This password was found in breached password lists %(num)d times and"
                " is not safe to use",
                count,
            )
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

    def validate_password(self, field) -> None:
        """Check for password match."""
        if not self.edit_user.password_is(field.data):
            raise forms.validators.ValidationError(_("Incorrect password"))


@User.forms('password_policy')
class PasswordPolicyForm(forms.Form):
    """Form to validate any candidate password against policy."""

    __expects__ = ('edit_user',)
    __returns__ = ('password_strength', 'is_weak', 'warning', 'suggestions')
    edit_user: User
    password_strength: Optional[int] = None
    is_weak: Optional[bool] = None
    warning: Optional[str] = None
    suggestions: Iterable[str] = ()

    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=PASSWORD_MAX_LENGTH),
        ],
    )

    def validate_password(self, field) -> None:
        """Test password strength and save resuls (no errors raised)."""
        user_inputs = []

        if self.edit_user:
            if self.edit_user.fullname:
                user_inputs.append(self.edit_user.fullname)

            for useremail in self.edit_user.emails:
                user_inputs.append(str(useremail))
            for emailclaim in self.edit_user.emailclaims:
                user_inputs.append(str(emailclaim))

            for userphone in self.edit_user.phones:
                user_inputs.append(str(userphone))

        tested_password = check_password_strength(
            field.data, user_inputs=user_inputs if user_inputs else None
        )
        self.password_strength = tested_password.score
        self.is_weak = tested_password.is_weak
        self.warning = tested_password.warning
        self.suggestions = tested_password.suggestions


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

    def validate_username(self, field) -> None:
        """Process username to retrieve user."""
        self.user, self.anchor = getuser(field.data, True)
        if self.user is None:
            raise forms.validators.ValidationError(
                _("Could not find a user with that id")
            )


@User.forms('password_create')
class PasswordCreateForm(forms.Form):
    """Form to accept a new password for a given user, without existing password."""

    __returns__ = ('password_strength',)
    __expects__ = ('edit_user',)
    edit_user: User
    password_strength: Optional[int] = None

    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=PASSWORD_MIN_LENGTH, max=PASSWORD_MAX_LENGTH),
            PasswordStrengthValidator(),
            pwned_password_validator,
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
    password_strength: Optional[int] = None

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
            pwned_password_validator,
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

    def validate_username(self, field) -> None:
        """Confirm the user provided by the client is who this form is meant for."""
        user = getuser(field.data)
        if user is None or user != self.edit_user:
            raise forms.validators.ValidationError(
                _("This does not match the user the reset code is for")
            )


@User.forms('password_change')
class PasswordChangeForm(forms.Form):
    """Form to change a user's password after confirming the old password."""

    __returns__ = ('password_strength',)
    __expects__ = ('edit_user',)
    edit_user: User
    password_strength: Optional[int] = None

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
            pwned_password_validator,
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

    def validate_old_password(self, field) -> None:
        """Validate the old password to be correct."""
        if self.edit_user is None:
            raise forms.validators.ValidationError(_("Not logged in"))
        if not self.edit_user.password_is(field.data):
            raise forms.validators.ValidationError(_("Incorrect password"))


def raise_username_error(reason: str) -> str:
    """Provide a user-friendly error message for a username field error."""
    if reason == 'blank':
        raise forms.validators.ValidationError(_("This is required"))
    if reason == 'long':
        raise forms.validators.ValidationError(_("This is too long"))
    if reason == 'invalid':
        raise forms.validators.ValidationError(
            _("Usernames can only have alphabets, numbers and underscores")
        )
    if reason == 'reserved':
        raise forms.validators.ValidationError(_("This username is reserved"))
    if reason in ('user', 'org'):
        raise forms.validators.ValidationError(_("This username has been taken"))
    raise forms.validators.ValidationError(_("This username is not available"))


@User.forms('main')
class AccountForm(forms.Form):
    """Form to edit basic account details."""

    edit_obj: User

    fullname = forms.StringField(
        __("Full name"),
        description=__("This is your name, not of your organization"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=User.__title_length__),
        ],
        filters=[forms.filters.strip()],
        render_kw={'autocomplete': 'name'},
    )
    username = forms.AnnotatedTextField(
        __("Username"),
        description=__(
            "A single word that is uniquely yours, for your account page and @mentions"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Profile.__name_length__),
        ],
        filters=nullable_strip_filters,
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

    def validate_username(self, field) -> None:
        """Validate if username is appropriately formatted and available to use."""
        reason = self.edit_obj.validate_name_candidate(field.data)
        if not reason:
            return  # Username is available
        raise_username_error(reason)


@User.forms('delete')
class AccountDeleteForm(forms.Form):
    """Delete user account."""

    confirm1 = forms.BooleanField(
        __(
            "I understand that deletion is permanent and my account cannot be recovered"
        ),
        validators=[forms.validators.DataRequired(__("You must accept this"))],
    )
    confirm2 = forms.BooleanField(
        __(
            "I understand that deleting my account will remove personal details such as"
            " my name and contact details, but not messages sent to other users, or"
            " public content such as comments, job posts and submissions to projects"
        ),
        description=__("Public content must be deleted individually"),
        validators=[forms.validators.DataRequired(__("You must accept this"))],
    )


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

    def validate_username(self, field) -> None:
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
        raise forms.validators.StopValidation(
            _("This email address is pending verification")
        )


@User.forms('email_add')
class NewEmailAddressForm(forms.RecaptchaForm):
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


@User.forms('email_primary')
class EmailPrimaryForm(forms.Form):
    """Form to mark an email address as a user's primary."""

    email_hash = forms.EmailField(
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
class NewPhoneForm(forms.RecaptchaForm):
    """Form to add a new mobile number (SMS-capable) to a user account."""

    __expects__ = ('edit_user',)
    edit_user: User

    phone = forms.TelField(
        __("Phone number"),
        validators=[
            forms.validators.DataRequired(),
            PhoneNumberAvailable(purpose='claim'),
        ],
        filters=strip_filters,
        description=__("Mobile numbers only, in Indian or international format"),
        render_kw={'autocomplete': 'tel'},
    )

    # TODO: Consider option "prefer WhatsApp" or "prefer secure messengers (WhatsApp)"

    enable_notifications = forms.BooleanField(
        __("Send notifications by SMS"),  # TODO: Add "or WhatsApp"
        description=__(
            "Unsubscribe anytime, and control what notifications are sent from the"
            " Notifications tab under account settings"
        ),
        default=True,
    )


@User.forms('phone_primary')
class PhonePrimaryForm(forms.Form):
    """Form to mark a phone number as a user's primary."""

    phone_hash = forms.StringField(
        __("Phone number"),
        validators=[forms.validators.DataRequired()],
        render_kw={
            'autocorrect': 'off',
            'autocapitalize': 'off',
            'autocomplete': 'tel',
        },
    )


class ModeratorReportForm(forms.Form):
    """Form to accept a comment moderator's report (spam or not spam)."""

    report_type = forms.SelectField(
        __("Report type"), coerce=int, validators=[forms.validators.InputRequired()]
    )

    def set_queries(self) -> None:
        """Prepare form for use."""
        self.report_type.choices = [
            (idx, report_type.title)
            for idx, report_type in MODERATOR_REPORT_TYPE.items()
        ]
