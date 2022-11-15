"""Helpers for forms."""

from __future__ import annotations

from typing import Optional

from flask import flash

from baseframe import _, __, forms
from coaster.auth import current_auth

from .. import app
from ..models import EmailAddress, Profile, UserEmailClaim, parse_video_url


class ProfileSelectField(forms.AutocompleteField):
    """Render an autocomplete field for selecting an account."""

    data: Optional[Profile]
    widget = forms.Select2Widget()
    multiple = False
    widget_autocomplete = True

    def _value(self):
        """Return value for HTML rendering."""
        if self.data:
            return self.data.name
        return ''

    def process_formdata(self, valuelist) -> None:
        """Process incoming form data."""
        if valuelist:
            self.data = Profile.query.filter(
                # Limit to non-suspended (active) profiles. Do not require profile to
                # be public as well
                Profile.name == valuelist[0],
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

    def __init__(self, purpose) -> None:
        if purpose not in ('use', 'claim', 'register'):
            raise ValueError("Invalid purpose")
        self.purpose = purpose

    def __call__(self, form, field) -> None:
        # Get actor (from existing obj, or current_auth.actor)
        actor = None
        if hasattr(form, 'edit_obj'):
            obj = form.edit_obj
            if obj and hasattr(obj, '__email_for__'):
                actor = getattr(obj, obj.__email_for__)
        if actor is None:
            actor = current_auth.actor

        # Call validator
        is_valid = EmailAddress.validate_for(
            actor, field.data, check_dns=True, new=self.purpose != 'use'
        )

        # Interpret code
        if not is_valid:
            if actor is not None:
                raise forms.validators.StopValidation(
                    _("This email address has been claimed by someone else")
                )
            raise forms.validators.StopValidation(
                _(
                    "This email address is already registered. You may want to try"
                    " logging in or resetting your password"
                )
            )
        if is_valid == 'invalid':
            raise forms.validators.StopValidation(
                _("This does not appear to be a valid email address")
            )
        if is_valid == 'nomx':
            raise forms.validators.StopValidation(
                _(
                    "The domain name of this email address is missing a DNS MX record."
                    " We require an MX record as missing MX is a strong indicator of"
                    " spam. Please ask your tech person to add MX to DNS"
                )
            )
        if is_valid == 'not_new':
            raise forms.validators.StopValidation(
                _("You have already registered this email address")
            )
        if is_valid == 'soft_fail':
            # XXX: In the absence of support for warnings in WTForms, we can only use
            # flash messages to communicate
            flash(
                _(
                    "This email address appears to be having temporary problems with"
                    " receiving email. Please use another if necessary"
                ),
                'warning',
            )
        elif is_valid == 'hard_fail':
            raise forms.validators.StopValidation(
                _(
                    "This email address is no longer valid. If you believe this to be"
                    " incorrect, email {support} asking for the address to be activated"
                ).format(support=app.config['SITE_SUPPORT_EMAIL'])
            )
        if is_valid is not True:
            app.logger.error("Unknown email address validation code: %r", is_valid)

        if is_valid and self.purpose == 'register':
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


def image_url_validator():
    """Customise ValidUrl for hosted image URL validation."""
    return forms.validators.ValidUrl(
        allowed_schemes=lambda: app.config.get('IMAGE_URL_SCHEMES', ('https',)),
        allowed_domains=lambda: app.config.get('IMAGE_URL_DOMAINS'),
        message_schemes=__("A https:// URL is required"),
        message_domains=__("Images must be hosted at images.hasgeek.com"),
    )


def video_url_validator(form, field):
    """Validate the video URL to be acceptable."""
    try:
        parse_video_url(field.data)
    except ValueError as exc:
        raise forms.validators.StopValidation(str(exc))


def tostr(value: object) -> str:
    """Cast truthy values to a string."""
    if value:
        return str(value)
    return ''


strip_filters = [tostr, forms.filters.strip()]
nullable_strip_filters = [tostr, forms.filters.strip(), forms.filters.none_if_empty()]
