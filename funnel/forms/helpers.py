"""Helpers for forms."""

from __future__ import annotations

from typing import Optional, Sequence
from typing_extensions import Literal
import json

from flask import flash

from baseframe import _, __, forms
from coaster.auth import current_auth

from .. import app
from ..models import (
    EmailAddress,
    PhoneNumber,
    Profile,
    User,
    UserEmailClaim,
    canonical_phone_number,
    parse_phone_number,
    parse_video_url,
)


class ProfileSelectField(forms.AutocompleteField):
    """Render an autocomplete field for selecting an account."""

    data: Optional[Profile]  # type: ignore[assignment]
    widget = forms.Select2Widget()
    multiple = False
    widget_autocomplete = True

    def _value(self) -> str:
        """Return value for HTML rendering."""
        if self.data is not None:
            return self.data.name
        return ''

    def process_formdata(self, valuelist: Sequence[str]) -> None:
        """Process incoming form data."""
        if valuelist:
            self.data = Profile.query.filter(
                # Limit to non-suspended (active) accounts. Do not require account to
                # be public as well
                Profile.name_is(valuelist[0]),
                Profile.is_active,
            ).one_or_none()
        else:
            self.data = None


class EmailAddressAvailable:
    """
    Validator for email address being available to the current user.

    This validator should always be used in conjunction with the ValidEmail validator,
    which should be used first. ValidEmail will check DNS records and inform the user
    if the email is malformed or the domain does not have appropriate records, while
    this one will only indicate if the email address is available for the user to claim.

    :param purpose: One of 'use', 'claim', 'register'
    """

    def __init__(self, purpose: Literal['use', 'claim', 'register']) -> None:
        if purpose not in ('use', 'claim', 'register'):
            raise ValueError("Invalid purpose")
        self.purpose = purpose

    def __call__(self, form: forms.Form, field: forms.Field) -> None:
        # Get actor (from form, or current_auth.actor)
        actor: Optional[User] = None
        if hasattr(form, 'edit_user'):
            actor = form.edit_user
        if actor is None:
            actor = current_auth.actor

        # Call validator
        has_error = EmailAddress.validate_for(
            actor, field.data, check_dns=True, new=self.purpose != 'use'
        )

        # Interpret code
        if has_error == 'taken':
            if actor is not None:
                if self.purpose == 'claim':
                    # Allow a claim on an existing ownership -- if verified, it will
                    # lead to account merger
                    return
                raise forms.validators.StopValidation(
                    _("This email address is linked to another account")
                )
            raise forms.validators.StopValidation(
                _(
                    "This email address is already registered. You may want to try"
                    " logging in or resetting your password"
                )
            )
        if has_error in ('invalid', 'nullmx'):
            raise forms.validators.StopValidation(
                _("This does not appear to be a valid email address")
            )
        if has_error == 'nomx':
            raise forms.validators.StopValidation(
                _(
                    "The domain name of this email address is missing a DNS MX record."
                    " We require an MX record as missing MX is a strong indicator of"
                    " spam. Please ask your tech person to add MX to DNS"
                )
            )
        if has_error == 'not_new':
            raise forms.validators.StopValidation(
                _("You have already registered this email address")
            )
        if has_error == 'soft_fail':
            # XXX: In the absence of support for warnings in WTForms, we can only use
            # flash messages to communicate
            flash(
                _(
                    "This email address appears to be having temporary problems with"
                    " receiving email. Please use another if necessary"
                ),
                'warning',
            )
            return
        if has_error == 'hard_fail':
            raise forms.validators.StopValidation(
                _(
                    "This email address is no longer valid. If you believe this to be"
                    " incorrect, email {support} asking for the address to be activated"
                ).format(support=app.config['SITE_SUPPORT_EMAIL'])
            )
        if has_error == 'blocked':
            raise forms.validators.StopValidation(
                _("This email address has been blocked from use")
            )
        if has_error is not None:
            app.logger.error("Unknown email address validation code: %r", has_error)

        if has_error is None and self.purpose == 'register':
            # One last check: is there an existing claim? If so, stop the user from
            # making a dupe account
            if UserEmailClaim.all(email=field.data).notempty():
                raise forms.validators.StopValidation(
                    _(
                        "You or someone else has made an account with this email"
                        " address but has not confirmed it. Do you need to reset your"
                        " password?"
                    )
                )


class PhoneNumberAvailable:
    """
    Validator for phone number being available to the current user.

    :param purpose: One of 'use', 'claim', 'register'
    """

    def __init__(self, purpose: Literal['use', 'claim', 'register']) -> None:
        if purpose not in ('use', 'claim', 'register'):
            raise ValueError("Invalid purpose")
        self.purpose = purpose

    def __call__(self, form: forms.Form, field: forms.Field) -> None:
        # Get actor (from existing obj, or current_auth.actor)
        actor: Optional[User] = None
        if hasattr(form, 'edit_user'):
            actor = form.edit_user
        if actor is None:
            actor = current_auth.actor

        parsed_number = parse_phone_number(field.data, sms=True, parsed=True)
        if parsed_number is False:
            raise forms.validators.StopValidation(
                _("This phone number cannot receive SMS messages")
            )
        if parsed_number is None:
            raise forms.validators.StopValidation(
                _("This does not appear to be a valid phone number")
            )

        # Save the parsed number back to the form field
        field.data = canonical_phone_number(parsed_number)
        # Call validator
        has_error = PhoneNumber.validate_for(
            actor, parsed_number, new=self.purpose != 'use'
        )

        # Interpret code
        if has_error == 'taken':
            if actor is not None:
                if self.purpose == 'claim':
                    # Allow a claim on an existing ownership -- if verified, it will
                    # lead to account merger.
                    return
                raise forms.validators.StopValidation(
                    _("This phone number is linked to another account")
                )
            raise forms.validators.StopValidation(
                _(
                    "This phone number is already registered. You may want to try"
                    " logging in or resetting your password"
                )
            )
        if has_error == 'invalid':
            raise forms.validators.StopValidation(
                _("This does not appear to be a valid phone number")
            )
        if has_error == 'not_new':
            raise forms.validators.StopValidation(
                _("You have already registered this phone number")
            )
        if has_error == 'blocked':
            raise forms.validators.StopValidation(
                _("This phone number has been blocked from use")
            )
        if has_error is not None:
            app.logger.error(  # type: ignore[unreachable]
                "Unknown phone number validation code: %r", has_error
            )


def image_url_validator() -> forms.validators.ValidUrl:
    """Customise ValidUrl for hosted image URL validation."""
    return forms.validators.ValidUrl(
        allowed_schemes=lambda: app.config.get('IMAGE_URL_SCHEMES', ('https',)),
        allowed_domains=lambda: app.config.get(  # type: ignore[arg-type, return-value]
            'IMAGE_URL_DOMAINS'
        ),
        message_schemes=__("A https:// URL is required"),
        message_domains=__("Images must be hosted at images.hasgeek.com"),
    )


def video_url_list_validator(form: forms.Form, field: forms.Field) -> None:
    """Validate all video URLs to be acceptable."""
    for url in field.data:
        try:
            parse_video_url(url)
        except ValueError:
            raise forms.validators.StopValidation(
                _("This video URL is not supported")
            ) from None


def video_url_validator(form: forms.Form, field: forms.Field) -> None:
    """Validate the video URL to be acceptable."""
    try:
        parse_video_url(field.data)
    except ValueError:
        raise forms.validators.StopValidation(
            _("This video URL is not supported")
        ) from None


def tostr(value: object) -> str:
    """Cast truthy values to a string."""
    if value:
        return str(value)
    return ''


def format_json(data: Union[dict, str, None]) -> str:
    """Return a dict as a formatted JSON string, and return a string unchanged."""
    if data:
        if isinstance(data, str):
            return data
        return json.dumps(data, indent=2, sort_keys=True)
    return ''


def validate_and_convert_json(form: forms.Form, field: forms.Field) -> None:
    """Confirm form data is valid JSON, and store it back as a parsed dict."""
    try:
        field.data = json.loads(field.data)
    except ValueError:
        raise forms.validators.StopValidation(_("Invalid JSON")) from None


strip_filters = [tostr, forms.filters.strip()]
nullable_strip_filters = [tostr, forms.filters.strip(), forms.filters.none_if_empty()]
nullable_json_filters = [
    format_json,
    forms.filters.strip(),
    forms.filters.none_if_empty(),
]
