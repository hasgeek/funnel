from flask import flash

from baseframe import _
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
    """

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
        is_valid = EmailAddress.validate_for(actor, field.data)

        # Interpret code
        if not is_valid:
            raise forms.validators.StopValidation(
                _("This email address belongs to another user")
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
