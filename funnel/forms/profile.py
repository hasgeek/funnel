# -*- coding: utf-8 -*-

from baseframe import _, __
import baseframe.forms as forms


class NewProfileForm(forms.Form):
    """Create a new profile."""

    profile = forms.RadioField(
        __("Organization"),
        validators=[forms.validators.DataRequired("Select an organization")],
        description=__("Select the organization you’d like to create a profile for"),
    )


class EditProfileForm(forms.Form):
    """Edit a profile."""

    description = forms.MarkdownField(
        __("Welcome message"),
        validators=[
            forms.validators.DataRequired(
                _("Please write a message for the landing page")
            )
        ],
        description=__("This welcome message will be shown on the landing page."),
    )
    logo_url = forms.URLField(
        __("Logo URL"),
        description=__("Profile logo"),
        validators=[
            forms.validators.Optional(),
            forms.validators.ValidUrl(),
            forms.validators.Length(max=2000),
        ],
    )
