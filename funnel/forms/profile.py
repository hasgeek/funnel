from __future__ import annotations

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
    """
    Edit a profile.

    A `profile` keyword argument is necessary for the ImgeeField.
    """

    __expects__ = ('profile',)

    description = forms.MarkdownField(
        __("Welcome message"),
        validators=[
            forms.validators.DataRequired(
                _("Please write a message for the profile page")
            )
        ],
        description=__("This message will be shown on the profile page"),
    )
    logo_url = forms.ImgeeField(
        label=__("Profile image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )
    website = forms.URLField(
        __("Website URL"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            forms.validators.URL(),
            forms.validators.ValidUrl(),
        ],
        filters=[forms.filters.none_if_empty()],
    )

    def set_queries(self):
        self.logo_url.profile = self.profile.name

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
    """
    Form for profile logo.

    A `profile` keyword argument is necessary for the ImgeeField.
    """

    __expects__ = ('profile',)

    logo_url = forms.ImgeeField(
        __("Profile image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )

    def set_queries(self):
        self.logo_url.widget_type = 'modal'
        self.logo_url.profile = self.profile.name


@Profile.forms('banner_image')
class ProfileBannerForm(forms.Form):
    """
    Form for profile banner.

    A `profile` keyword argument is necessary for the ImgeeField.
    """

    __expects__ = ('profile',)

    banner_image_url = forms.ImgeeField(
        __("Banner image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )

    def set_queries(self):
        self.banner_image_url.widget_type = 'modal'
        self.banner_image_url.profile = self.profile.name
