# -*- coding: utf-8 -*-

from baseframe import _, __
import baseframe.forms as forms

from ..models import Profile
from .organization import OrganizationForm

__all__ = ['ProfileForm']


@Profile.forms('main')
class ProfileForm(OrganizationForm):
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
