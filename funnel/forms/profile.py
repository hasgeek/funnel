from flask import current_app

from baseframe import _, __
import baseframe.forms as forms

from ..models import Profile
from .organization import OrganizationForm

__all__ = ['ProfileForm', 'ProfileTransitionForm']


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
            forms.validators.ValidUrl(
                allowed_schemes=lambda: current_app.config.get(
                    'IMAGE_URL_SCHEMES', ('https',)
                ),
                allowed_domains=lambda: current_app.config.get('IMAGE_URL_DOMAINS'),
                message_schemes=__("A https:// URL is required"),
                message_domains=__("Images must be hosted at images.hasgeek.com"),
            ),
            forms.validators.Length(max=2000),
        ],
    )


@Profile.forms('transition')
class ProfileTransitionForm(forms.Form):
    transition = forms.SelectField(
        __("Project status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.transition.choices = list(self.edit_obj.state.transitions().items())
