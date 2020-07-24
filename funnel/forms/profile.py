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
                _("Please write a message for the profile page")
            )
        ],
        description=__("This message will be shown on the profile page"),
    )
    logo_url = forms.URLField(
        __("Profile image URL"),
        description=__(
            "From images.hasgeek.com, with 1:1 aspect ratio."
            " Should be < 30 kB in size"
        ),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )

    def make_for_user(self):
        self.title.label.text = __("Your name")
        self.title.description = __(
            "Your full name, in the form others can recognise you by"
        )
        self.name.description = __(
            "A short name for mentioning you with @username, and the URL to your"
            " profile page. Single word containing letters, numbers and dashes only."
            " Pick something permanent: changing it will break existing links from"
            " around the web"
        )
        self.description.label.text = __("About you")
        self.description.description = __(
            "This message will be shown on the profile page"
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
        __("Profile image URL"),
        description=__(
            "From images.hasgeek.com, with 1:1 aspect ratio."
            " Should be < 30 kB in size"
        ),
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
        description=__(
            "From images.hasgeek.com, with 8:3 aspect ratio."
            " Should be < 100 kB in size"
        ),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )
