from __future__ import annotations

import re

from baseframe import _, __
from baseframe.forms.sqlalchemy import AvailableName
from coaster.utils import sorted_timezones, utcnow
import baseframe.forms as forms

from ..models import Project, Rsvp, SavedProject
from .helpers import image_url_validator, nullable_strip_filters

__all__ = [
    'CfpForm',
    'ProjectCfpTransitionForm',
    'ProjectForm',
    'ProjectLivestreamForm',
    'ProjectNameForm',
    'ProjectTransitionForm',
    'ProjectBannerForm',
    'RsvpTransitionForm',
    'SavedProjectForm',
]

double_quote_re = re.compile(r'["“”]')


@Project.forms('main')
class ProjectForm(forms.Form):
    """
    Form to create or edit a project.

    A `profile` keyword argument is necessary for the ImgeeField.
    """

    __expects__ = ('profile',)

    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    tagline = forms.StringField(
        __("Tagline"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)],
        filters=[forms.filters.strip()],
        description=__("One line description of the project"),
    )
    location = forms.StringField(
        __("Location"),
        description=__(
            '“Online” if this is online-only, else the city or region (without quotes)'
        ),
        validators=[
            forms.validators.DataRequired(
                __("If this project is online-only, use “Online”")
            ),
            forms.validators.Length(
                min=3, max=50, message=__("%(max)d characters maximum")
            ),
        ],
        filters=[forms.filters.strip()],
    )
    start_at = forms.DateTimeField(
        __("Optional - Starting time"),
        validators=[forms.validators.Optional()],
        naive=False,
    )
    end_at = forms.DateTimeField(
        __("Optional - Ending time"),
        validators=[
            forms.validators.RequiredIf(
                'start_at',
                message=__("This is required when starting time is specified"),
            ),
            forms.validators.AllowedIf(
                'start_at', message=__("This requires a starting time too")
            ),
            forms.validators.Optional(),  # Stop the next validator if field is empty
            forms.validators.GreaterThan(
                'start_at', __("This must be after the starting time")
            ),
        ],
        naive=False,
    )
    timezone = forms.SelectField(
        __("Timezone"),
        description=__("The timezone in which this event occurs"),
        validators=[forms.validators.DataRequired()],
        choices=sorted_timezones(),
        default='UTC',
    )
    bg_image = forms.ImgeeField(
        __("Banner image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
        filters=nullable_strip_filters,
    )
    description = forms.MarkdownField(
        __("Project description"),
        validators=[forms.validators.DataRequired()],
        description=__("Landing page contents"),
    )

    def validate_location(self, field):
        if re.search(double_quote_re, field.data) is not None:
            raise forms.ValidationError(
                __("Quotes are not necessary in the location name")
            )

    def set_queries(self):
        self.bg_image.profile = self.profile.name
        if self.edit_obj and self.edit_obj.schedule_start_at:
            # Don't allow user to directly manipulate timestamps when it's done via
            # Session objects
            del self.start_at
            del self.end_at


@Project.forms('featured')
class ProjectFeaturedForm(forms.Form):
    site_featured = forms.BooleanField(
        __("Feature this project"), validators=[forms.validators.InputRequired()]
    )


class ProjectLivestreamForm(forms.Form):
    livestream_urls = forms.TextListField(
        __(
            "Livestream URLs. One per line. Must be on YouTube or Vimeo."
            " Must begin with https://"
        ),
        filters=[forms.filters.strip_each()],
        validators=[
            forms.validators.Optional(),
            forms.validators.ForEach(
                [
                    forms.validators.URL(),
                    forms.validators.ValidUrl(
                        allowed_schemes=('https',),
                        allowed_domains=(
                            'www.youtube.com',
                            'youtube.com',
                            'youtu.be',
                            'y2u.be',
                            'www.vimeo.com',
                            'vimeo.com',
                        ),
                        message_schemes=__("A https:// URL is required"),
                        message_domains=__("Livestream must be on YouTube or Vimeo"),
                    ),
                ]
            ),
        ],
    )


class ProjectNameForm(forms.Form):
    name = forms.AnnotatedTextField(
        __("Custom URL"),
        description=__(
            "Customize the URL of your project."
            " Use lowercase letters, numbers and dashes only."
            " Including a date is recommended"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Project.__name_length__),
            forms.validators.ValidName(
                __(
                    "This URL contains unsupported characters. It can contain"
                    " lowercase letters, numbers and hyphens only"
                )
            ),
            AvailableName(),
        ],
        filters=[forms.filters.strip()],
        prefix="https://hasgeek.com/<profile>/",
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )


class ProjectBannerForm(forms.Form):
    """
    Form for project banner.

    A `profile` keyword argument is necessary for the ImgeeField.
    """

    __expects__ = ('profile',)

    bg_image = forms.ImgeeField(
        __("Banner image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
        filters=nullable_strip_filters,
    )

    def set_queries(self):
        self.bg_image.widget_type = 'modal'
        self.bg_image.profile = self.profile.name


@Project.forms('cfp')
class CfpForm(forms.Form):
    instructions = forms.MarkdownField(
        __("Guidelines"),
        validators=[forms.validators.DataRequired()],
        default='',
        description=__(
            "Set guidelines for the type of submissions your project is accepting,"
            " your review process, and anything else relevant to the submission"
        ),
    )
    cfp_end_at = forms.DateTimeField(
        __("Submissions close at"),
        description=__("Optional – Leave blank to have no closing date"),
        validators=[forms.validators.Optional()],
        naive=False,
    )

    def validate_cfp_end_at(self, field):
        if field.data <= utcnow():
            raise forms.StopValidation(_("Closing date must be in the future"))


@Project.forms('transition')
class ProjectTransitionForm(forms.Form):
    transition = forms.SelectField(
        __("Status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.transition.choices = list(self.edit_obj.state.transitions().items())


@Project.forms('cfp_transition')
class ProjectCfpTransitionForm(forms.Form):
    open = forms.BooleanField(
        __("Open submissions"), validators=[forms.validators.InputRequired()]
    )

    def get_open(self, obj):
        self.open.data = bool(obj.cfp_state.OPEN)

    def set_open(self, obj):
        if self.open.data and not obj.cfp_state.OPEN:
            # Checkbox: yes, but CfP state is not open, so open it
            obj.open_cfp()
        elif not self.open.data and obj.cfp_state.OPEN:
            # Checkbox: no, but CfP state is open, so close it
            obj.close_cfp()
        # No action required in all other cases


@SavedProject.forms('main')
class SavedProjectForm(forms.Form):
    save = forms.BooleanField(
        __("Save this project?"), validators=[forms.validators.InputRequired()]
    )
    description = forms.StringField(
        __("Note to self"),
        validators=[forms.validators.Optional()],
        filters=[forms.filters.strip()],
    )


@Rsvp.forms('transition')
class RsvpTransitionForm(forms.Form):
    transition = forms.SelectField(
        __("Status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        # Usually you need to use an instance's state.transitions to find
        # all the valid transitions for the current state of the instance.
        # But for RSVP, we're showing all the options all the time, so this
        # call is valid. We're also doing this because we want to load the
        # options in the form even without an Rsvp instance.
        self.transition.choices = [
            (transition_name, getattr(Rsvp, transition_name))
            for transition_name in Rsvp.state.statemanager.transitions
        ]
