from collections import namedtuple

from flask import request

from baseframe import _, __
from coaster.auth import current_auth
from coaster.utils import nullstr, sorted_timezones
import baseframe.forms as forms

from ..models import (
    MODERATOR_REPORT_TYPE,
    Profile,
    User,
    UserEmailClaim,
    UserPhone,
    UserPhoneClaim,
    getuser,
    notification_type_registry,
    password_policy,
)
from ..transports import platform_transports
from ..utils import strip_phone, valid_phone
from .helpers import EmailAddressAvailable

__all__ = [
    'RegisterForm',
    'PasswordCreateForm',
    'PasswordPolicyForm',
    'PasswordResetRequestForm',
    'PasswordResetForm',
    'PasswordChangeForm',
    'AccountForm',
    'UnsubscribeForm',
    'SetNotificationPreferenceForm',
    'EmailPrimaryForm',
    'ModeratorReportForm',
    'NewEmailAddressForm',
    'NewPhoneForm',
    'PhonePrimaryForm',
    'VerifyEmailForm',
    'VerifyPhoneForm',
    'supported_locales',
    'timezone_identifiers',
    'transport_labels',
]


timezones = sorted_timezones()
timezone_identifiers = dict(timezones)

supported_locales = {
    'en': __("English"),
    'hi': __("Hindi (beta; incomplete)"),
}

TransportLabels = namedtuple(
    'TransportLabels',
    [
        'title',
        'requirement',
        'unsubscribe_form',
        'switch',
        'enabled_main',
        'enabled',
        'disabled_main',
        'disabled',
    ],
)
transport_labels = {
    'email': TransportLabels(
        __("Email"),
        __("To enable, add a verified email address"),
        __("Notify me by email"),
        __("Email notifications"),
        __("Enabled selected email notifications"),
        __("Enabled this email notification"),
        __("Disabled all email notifications"),
        __("Disabled this email notification"),
    ),
    'sms': TransportLabels(
        __("SMS"),
        __("To enable, add a verified phone number"),
        __("Notify me by SMS"),
        __("SMS notifications"),
        __("Enabled selected SMS notifications"),
        __("Enabled this SMS notification"),
        __("Disabled all SMS notifications"),
        __("Disabled this SMS notification"),
    ),
    'webpush': TransportLabels(
        __("Browser"),
        __("To enable, allow push notifications in the browser"),
        __("Notify me with browser notifications"),
        __("Push notifications"),
        __("Enabled selected push notifications"),
        __("Enabled this push notification"),
        __("Disabled all push notifications"),
        __("Disabled this push notification"),
    ),
    'telegram': TransportLabels(
        __("Telegram"),
        __("To enable, link your Telegram account"),
        __("Notify me on Telegram"),
        __("Telegram notifications"),
        __("Enabled selected Telegram notifications"),
        __("Enabled this Telegram notification"),
        __("Disabled all Telegram notifications"),
        __("Disabled this Telegram notification"),
    ),
    'whatsapp': TransportLabels(
        __("WhatsApp"),
        __("To enable, add your WhatsApp number"),
        __("Notify me on WhatsApp"),
        __("WhatsApp notifications"),
        __("Enabled selected WhatsApp notifications"),
        __("Enabled this WhatsApp notification"),
        __("Disabled all WhatsApp notifications"),
        __("Disabled this WhatsApp notification"),
    ),
}


class PasswordStrengthValidator:
    default_message = _(
        "This password is too simple. Add complexity by making it longer and using "
        "a mix of upper and lower case letters, numbers and symbols"
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

        tested_password = password_policy.test_password(
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
    )
    email = forms.EmailField(
        __("Email address"),
        validators=[
            forms.validators.DataRequired(),
            EmailAddressAvailable(purpose='register'),
        ],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    password = forms.PasswordField(
        __("Password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=8, max=40),
            PasswordStrengthValidator(user_input_fields=['fullname', 'email']),
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


@User.forms('password_policy')
class PasswordPolicyForm(forms.Form):
    candidate = forms.StringField(
        __("Password"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=40)],
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
            forms.validators.Length(min=8, max=40),
            PasswordStrengthValidator(),
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
            forms.validators.Length(min=8, max=40),
            PasswordStrengthValidator(user_input_fields=['username']),
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

    def validate_username(self, field):
        user = getuser(field.data)
        if user is None or user != self.edit_user:
            raise forms.ValidationError(
                _(
                    "This username or email does not match the user the reset code is "
                    "for"
                )
            )


@User.forms('password_change')
class PasswordChangeForm(forms.Form):
    __returns__ = ('password_strength',)
    __expects__ = ('edit_user',)

    old_password = forms.PasswordField(
        __("Current password"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=40)],
    )
    password = forms.PasswordField(
        __("New password"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(min=8, max=40),
            PasswordStrengthValidator(),
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

    def validate_old_password(self, field):
        if self.edit_user is None:
            raise forms.ValidationError(_("Not logged in"))
        if not self.edit_user.password_is(field.data):
            raise forms.ValidationError(_("Incorrect password"))


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
    )
    email = forms.EmailField(
        __("Email address"),
        description=__("Required for sending you tickets, invoices and notifications"),
        validators=[
            forms.validators.DataRequired(),
            EmailAddressAvailable(purpose='use'),
        ],
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    username = forms.AnnotatedTextField(
        __("Username"),
        description=__(
            "Single word that can contain letters, numbers and dashes. "
            "You need a username to have a public profile"
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
            "Where in the world are you? Dates and times will be shown in your local "
            "timezone"
        ),
        validators=[forms.validators.DataRequired()],
        choices=timezones,
        widget_attrs={},
    )
    auto_timezone = forms.BooleanField(__("Use your device’s timezone"))
    locale = forms.SelectField(
        __("Locale"),
        description=__("Your preferred UI language"),
        choices=supported_locales.items(),
    )
    auto_locale = forms.BooleanField(__("Use your device’s language"))

    def validate_username(self, field):
        reason = self.edit_obj.validate_name_candidate(field.data)
        if not reason:
            return  # Username is available
        if reason == 'invalid':
            raise forms.ValidationError(
                _(
                    "Usernames can only have alphabets, numbers and dashes (except at "
                    "the ends)"
                )
            )
        elif reason == 'reserved':
            raise forms.ValidationError(_("This username is reserved"))
        elif reason in ('user', 'org'):
            raise forms.ValidationError(_("This username has been taken"))
        else:
            raise forms.ValidationError(_("This username is not available"))


@User.forms('unsubscribe')
class UnsubscribeForm(forms.Form):
    __expects__ = ('edit_user', 'transport', 'notification_type')

    # To consider: Replace the field's ListWidget with a GroupedListWidget, and show all
    # known notifications by category, not just the ones the user has received a
    # notification for. This will avoid a dark pattern wherein a user keeps getting
    # subscribed to new types of notifications, a problem Twitter had when they
    # attempted to engage dormant accounts by inventing new reasons to email them.
    # However, also consider that this will be a long and overwhelming list, and will
    # not help with new notification types added after the user visits this list. The
    # better option may be to set notification preferences based on previous
    # preferences. A crude form of this exists in the NotificationPreferences class,
    # but it should be smarter about defaults per category of notification.

    main = forms.BooleanField(
        __("Notify me"), description=__("Uncheck this to disable all notifications"),
    )

    types = forms.SelectMultipleField(
        __("Or disable only a specific notification"),
        widget=forms.ListWidget(),
        option_widget=forms.CheckboxInput(),
    )

    # This token is validated in the view, not here, because it has to be valid in the
    # GET request itself, and the UI flow is very dependent on the validation error.
    token = forms.HiddenField(
        __("Unsubscribe token"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        # Populate choices with all notification types that the user has a preference
        # row for.
        if self.transport in transport_labels:
            self.main.label.text = transport_labels[self.transport].unsubscribe_form
        self.types.choices = [
            (ntype, notification_type_registry[ntype].description)
            for ntype in self.edit_user.notification_preferences
            if ntype in notification_type_registry
            and notification_type_registry[ntype].allow_transport(self.transport)
        ]

        if request.method == 'GET':
            # Populate data with all notification types for which the user has the
            # current transport enabled
            self.main.data = self.edit_user.main_notification_preferences.by_transport(
                self.transport
            )
            self.types.data = [
                ntype
                for ntype, user_prefs in self.edit_user.notification_preferences.items()
                if user_prefs.by_transport(self.transport)
            ]

    def save_to_user(self):
        # self.types.data will only contain the enabled preferences. Therefore, iterate
        # through all choices and toggle true or false based on whether it's in the
        # enabled list. This uses dict access instead of .get because set_queries
        # also populates from this list.
        self.edit_user.main_notification_preferences.set_transport(
            self.transport, self.main.data
        )
        for ntype, title in self.types.choices:
            self.edit_user.notification_preferences[ntype].set_transport(
                self.transport, ntype in self.types.data
            )


@User.forms('set_notification_preference')
class SetNotificationPreferenceForm(forms.Form):
    """Set one notification preference."""

    notification_type = forms.SelectField(__("Notification type"))
    transport = forms.SelectField(
        __("Transport"), validators=[forms.validators.DataRequired()],
    )
    enabled = forms.BooleanField(__("Enable this transport"))

    def set_queries(self):
        # The main switch is special-cased with an empty string for notification type
        self.notification_type.choices = [('', __("Main switch"))] + [
            (ntype, cls.description)
            for ntype, cls in notification_type_registry.items()
        ]
        self.transport.choices = [
            (transport, transport)
            for transport in platform_transports
            if platform_transports[transport]
        ]

    def status_message(self):
        """Render a success or error message."""
        if self.errors:
            # Flatten errors into a single string because typically this will only
            # be a CSRF error.
            return ' '.join(' '.join(message) for message in self.errors.values())
        if self.notification_type.data == '':
            return (
                transport_labels[self.transport.data].enabled_main
                if self.enabled.data
                else transport_labels[self.transport.data].disabled_main
            )
        return (
            transport_labels[self.transport.data].enabled
            if self.enabled.data
            else transport_labels[self.transport.data].disabled
        )


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
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )
    type = forms.RadioField(  # NOQA: A003
        __("Type"),
        coerce=nullstr,
        validators=[forms.validators.Optional()],
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
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )


@User.forms('email_verify')
class VerifyEmailForm(forms.Form):
    pass


@User.forms('phone_add')
class NewPhoneForm(forms.RecaptchaForm):
    phone = forms.TelField(
        __("Phone number"),
        default='+91',
        validators=[forms.validators.DataRequired()],
        description=__(
            "Mobile numbers only at this time. Please prefix with '+' and country code."
        ),
    )

    # Temporarily removed since we only support mobile numbers at this time. When phone
    # call validation is added, we can ask for other types of numbers:

    # type = forms.RadioField(__("Type"), coerce=nullstr,
    #     validators=[forms.validators.Optional()],
    #     choices=[
    #         (__(u"Mobile"), __(u"Mobile")),
    #         (__(u"Home"), __(u"Home")),
    #         (__(u"Work"), __(u"Work")),
    #         (__(u"Other"), __(u"Other"))])

    def validate_phone(self, field):
        # TODO: Use the phonenumbers library to validate this

        # Step 1: Remove punctuation in number
        number = strip_phone(field.data)
        # Step 2: Check length
        if len(number) > 16:
            raise forms.ValidationError(
                _("This is too long to be a valid phone number")
            )
        # Step 3: Validate number format
        if not valid_phone(number):
            raise forms.ValidationError(
                _(
                    "Invalid phone number (must be in international format with a "
                    "leading + (plus) symbol)"
                )
            )
        # Step 4: Check if Indian number (startswith('+91'))
        if number.startswith('+91') and len(number) != 13:
            raise forms.ValidationError(
                _("This does not appear to be a valid Indian mobile number")
            )
        # Step 5: Check if number has already been claimed
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
        widget_attrs={'pattern': '[0-9]*', 'autocomplete': 'off'},
    )

    def validate_verification_code(self, field):
        # self.phoneclaim is set by the view before calling form.validate()
        if self.phoneclaim.verification_code != field.data:
            raise forms.ValidationError(_("Verification code does not match"))


class ModeratorReportForm(forms.Form):
    report_type = forms.SelectField(
        __("Report type"), coerce=int, validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.report_type.choices = [
            (idx, report_type.title)
            for idx, report_type in MODERATOR_REPORT_TYPE.items()
        ]
