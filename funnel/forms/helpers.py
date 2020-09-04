from flask import current_app, flash

from baseframe import _, __
from coaster.auth import current_auth
import baseframe.forms as forms

from ..models import EmailAddress


class EmailAddressAvailable:
    """
    Validator for email address being available to the current user.

    This validator should always be used in conjunction with the ValidEmail validator,
    which should be used first. ValidEmail will check DNS records and inform the user
    if the email is malformed or the domain does not have appropriate records, while
    this one will only indicate if the email address is available for the user to claim.

    :param purpose: One of 'use', 'claim', 'register'
    """

    def __init__(self, purpose):
        if purpose not in ('use', 'claim', 'register'):
            raise ValueError("Invalid purpose")
        self.purpose = purpose

    def __call__(self, form, field):
        # Get actor (from existing obj, or current_auth.actor)
        actor = None
        if hasattr(form, 'edit_obj'):
            obj = form.edit_obj
            if obj and hasattr(obj, '__email_for__'):
                actor = getattr(obj, obj.__email_for__)
        if not actor:
            actor = current_auth.actor

        # Call validator
        is_valid = EmailAddress.validate_for(
            actor, field.data, check_dns=True, new=self.purpose != 'use',
        )

        # Interpret code
        if not is_valid:
            if actor:
                raise forms.validators.StopValidation(
                    _("This email address has been claimed by someone else")
                )
            raise forms.validators.StopValidation(
                _(
                    "This email address is already registered. You may want to try"
                    " logging in or resetting your password"
                )
            )
        elif is_valid == 'invalid':
            raise forms.validators.StopValidation(
                _("This does not appear to be a valid email address.")
            )
        elif is_valid == 'nomx':
            raise forms.validators.StopValidation(
                _(
                    "The domain name of this email address is missing a DNS MX record."
                    " We require an MX record as missing MX is a strong indicator of"
                    " spam. Please ask your tech person to add MX to DNS."
                )
            )
        elif is_valid == 'not_new' and self.purpose == 'register':
            raise forms.validators.StopValidation(
                _(
                    "You or someone else has made an account with this email address"
                    " but not confirmed it. Do you need to reset your password?"
                )
            )
        elif is_valid == 'not_new' and self.purpose == 'claim':
            raise forms.validators.StopValidation(
                _("You have already registered this email address")
            )
        elif is_valid == 'soft_fail':
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
                    " in error, please email us at support@hasgeek.com"
                )
            )


def image_url_validator():
    return forms.validators.ValidUrl(
        allowed_schemes=lambda: current_app.config.get('IMAGE_URL_SCHEMES', ('https',)),
        allowed_domains=lambda: current_app.config.get('IMAGE_URL_DOMAINS'),
        message_schemes=__("A https:// URL is required"),
        message_domains=__("Images must be hosted at images.hasgeek.com"),
    )
