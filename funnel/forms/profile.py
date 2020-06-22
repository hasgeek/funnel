from baseframe import _, __
import baseframe.forms as forms

from ..models import Profile
from .helpers import image_url_validator
from .organization import OrganizationForm

__all__ = [
    'ProfileForm',
    'ProfileLogoForm',
    'ProfileBannerForm',
    'ProfileTransitionForm',
]


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
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )


@Profile.forms('transition')
class ProfileTransitionForm(forms.Form):
    transition = forms.SelectField(
        __("Project status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.transition.choices = list(self.edit_obj.state.transitions().items())


@Profile.forms('logo')
class ProfileLogoForm(forms.Form):
    logo_url = forms.URLField(
        __("Logo image URL"),
        description=__("URL for profile logo image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )


@Profile.forms('banner_image')
class ProfileBannerForm(forms.Form):
    banner_image_url = forms.URLField(
        __("Banner image URL"),
        description=__("URL for profile banner image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )
