import re

from baseframe import __
from baseframe.forms.sqlalchemy import AvailableName
from coaster.utils import sorted_timezones
import baseframe.forms as forms

from ..models import Project, Rsvp, SavedProject
from .helpers import image_url_validator

__all__ = [
    'CfpForm',
    'ProjectCfpTransitionForm',
    'ProjectForm',
    'ProjectLivestreamForm',
    'ProjectNameForm',
    'ProjectScheduleTransitionForm',
    'ProjectTransitionForm',
    'ProjectBannerForm',
    'RsvpTransitionForm',
    'SavedProjectForm',
]

double_quote_re = re.compile(r'["“”]')


@Project.forms('main')
class ProjectForm(forms.Form):
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
        if self.edit_obj is not None:
            self.bg_image.profile = self.edit_obj.profile.name


class ProjectLivestreamForm(forms.Form):
    livestream_urls = forms.TextListField(
        __(
            "Livestream URLs. One per line. Must be on YouTube or Vimeo. "
            "Must begin with https://"
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
            "Customize the URL of your project. "
            "Use lowercase letters, numbers and dashes only. "
            "Including a date is recommended"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Project.__name_length__),
            forms.validators.ValidName(
                __(
                    "This URL contains unsupported characters. It can contain "
                    "lowercase letters, numbers and hyphens only."
                )
            ),
            AvailableName(),
        ],
        prefix="https://hasgeek.com/<profile>/",
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )


class ProjectBannerForm(forms.Form):
    bg_image = forms.ImgeeField(
        __("Banner image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
    )

    def set_queries(self):
        self.bg_image.widget_type = 'modal'
        if self.edit_obj:
            self.bg_image.profile = self.edit_obj.profile.name


@Project.forms('cfp')
class CfpForm(forms.Form):
    instructions = forms.MarkdownField(
        __("Proposal guidelines"),
        validators=[forms.validators.DataRequired()],
        default='',
        description=__(
            "Set guidelines for the type of sessions"
            "(talks, workshops, other format) your project is accepting, "
            "your review process and any other info for participants"
        ),
    )
    cfp_start_at = forms.DateTimeField(
        __("Proposal submissions open at"),
        validators=[forms.validators.Optional()],
        naive=False,
    )
    cfp_end_at = forms.DateTimeField(
        __("Proposal submissions close at"),
        validators=[
            forms.validators.Optional(),
            forms.validators.AllowedIf(
                'cfp_start_at',
                message=__("This requires open time for submissions to be specified"),
            ),
            forms.validators.GreaterThanEqualTo(
                'cfp_start_at', __("Submissions cannot close before they open")
            ),
        ],
        naive=False,
    )


@Project.forms('transition')
class ProjectTransitionForm(forms.Form):
    transition = forms.SelectField(
        __("Status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.transition.choices = list(self.edit_obj.state.transitions().items())


@Project.forms('schedule_transition')
class ProjectScheduleTransitionForm(forms.Form):
    schedule_transition = forms.SelectField(
        __("Schedule status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.schedule_transition.choices = list(
            self.edit_obj.schedule_state.transitions().items()
        )


@Project.forms('cfp_transition')
class ProjectCfpTransitionForm(forms.Form):
    cfp_transition = forms.SelectField(
        __("CfP status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.cfp_transition.choices = list(
            self.edit_obj.cfp_state.transitions().items()
        )


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
