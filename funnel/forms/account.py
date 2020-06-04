from baseframe import _, __
from coaster.auth import current_auth
from coaster.utils import nullstr, sorted_timezones
import baseframe.forms as forms

from ..models import (
    MODERATOR_REPORT_TYPE,
    Profile,
    User,
    UserEmail,
    UserEmailClaim,
    UserPhone,
    UserPhoneClaim,
    getuser,
    password_policy,
)
from ..utils import strip_phone, valid_phone

__all__ = [
    'PasswordResetRequestForm',
    'PasswordResetForm',
    'PasswordChangeForm',
    'AccountForm',
    'EmailPrimaryForm',
    'ModeratorReportForm',
    'NewEmailAddressForm',
    'NewPhoneForm',
    'PhonePrimaryForm',
    'VerifyEmailForm',
    'VerifyPhoneForm',
]


timezones = sorted_timezones()


def password_strength_validator(form, field):
    # Test the candidate password
    tested_password = password_policy.password(field.data)
    # Stick password strength into the form for logging in the view and possibly
    # rendering into UI
    form.password_strength = float(tested_password.strength())
    # No test failures? All good then
    if not tested_password.test():
        return
    # Tell the user to make up a better password
    raise forms.validators.StopValidation(
        _(
            "This password is too simple. Add complexity by making it longer and using "
            "a mix of upper and lower case letters, numbers and symbols"
        )
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

    old_password = forms.PasswordField(
        __("Current password"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=40)],
    )
    password = forms.PasswordField(
        __("New password"),
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
        validators=[forms.validators.DataRequired(), forms.validators.ValidEmail()],
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
    )

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

    # TODO: Move to function and place before ValidEmail()
    def validate_email(self, field):
        existing = UserEmail.get(email=field.data)
        if existing is not None and existing.user != self.edit_obj:
            raise forms.ValidationError(
                _("This email address has been claimed by another user")
            )


@User.forms('email_add')
class NewEmailAddressForm(forms.RecaptchaForm):
    email = forms.EmailField(
        __("Email address"),
        validators=[forms.validators.DataRequired(), forms.validators.ValidEmail()],
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

    # TODO: Move to function and place before ValidEmail()
    def validate_email(self, field):
        field.data = field.data.lower()  # Convert to lowercase
        existing = UserEmail.get(email=field.data)
        if existing is not None:
            if existing.user == current_auth.user:
                raise forms.ValidationError(
                    _("You have already registered this email address")
                )
            else:
                raise forms.ValidationError(
                    _("This email address has already been claimed")
                )
        existing = UserEmailClaim.get_for(user=current_auth.user, email=field.data)
        if existing is not None:
            raise forms.ValidationError(_("This email address is pending verification"))


@User.forms('email_primary')
class EmailPrimaryForm(forms.Form):
    email = forms.EmailField(
        __("Email address"),
        validators=[forms.validators.DataRequired(), forms.validators.ValidEmail()],
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
