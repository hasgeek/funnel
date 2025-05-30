"""Forms for a project."""

from __future__ import annotations

import re
from typing import cast

from baseframe import _, __, forms
from baseframe.forms.sqlalchemy import AvailableName, QuerySelectField
from coaster.utils import sorted_timezones, utcnow

from ..models import Account, Project, Rsvp, SavedProject
from .helpers import (
    AccountSelectField,
    image_url_validator,
    nullable_json_filters,
    nullable_strip_filters,
    validate_and_convert_json,
    video_url_list_validator,
)

__all__ = [
    'CfpForm',
    'ProjectAssignParentForm',
    'ProjectBannerForm',
    'ProjectCfpTransitionForm',
    'ProjectFeaturedForm',
    'ProjectForm',
    'ProjectLivestreamForm',
    'ProjectNameForm',
    'ProjectRegisterForm',
    'ProjectSponsorForm',
    'ProjectTransitionForm',
    'RsvpTransitionForm',
    'SavedProjectForm',
]

double_quote_re = re.compile(r'["“”]')


@Project.forms('main')
class ProjectForm(forms.Form):
    """
    Form to create or edit a project.

    An `account` keyword argument is necessary for the ImgeeField.
    """

    __expects__ = ('account',)
    account: Account
    edit_obj: Project | None

    title = forms.StringField(
        __("Title"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Project.__title_length__),
        ],
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
        __("Optional – Starting time"),
        validators=[forms.validators.Optional()],
        naive=False,
    )
    end_at = forms.DateTimeField(
        __("Optional – Ending time"),
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

    def validate_location(self, field: forms.Field) -> None:
        """Validate location field to not have quotes (from copy paste of hint)."""
        if re.search(double_quote_re, field.data) is not None:
            raise forms.validators.ValidationError(
                __("Quotes are not necessary in the location name")
            )

    def __post_init__(self) -> None:
        self.bg_image.profile = self.account.name or self.account.buid
        if self.edit_obj is not None and self.edit_obj.schedule_start_at:
            # Don't allow user to directly manipulate timestamps when it's done via
            # Session objects
            del self.start_at
            del self.end_at


@Project.forms('featured')
class ProjectFeaturedForm(forms.Form):
    """Form to mark a project as featured site-wide."""

    site_featured = forms.BooleanField(
        __("Feature this project"), validators=[forms.validators.InputRequired()]
    )


class ProjectLivestreamForm(forms.Form):
    """Form to add a livestream URL to a project."""

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
            video_url_list_validator,
        ],
    )

    is_restricted_video = forms.BooleanField(
        __("Restrict livestream to participants only")
    )


class ProjectNameForm(forms.Form):
    """Form to change the URL name of a project."""

    # TODO: Add validators for `account` and unique name here instead of delegating to
    # the view. Also add `__post_init__` method to change ``name.prefix``

    name = forms.AnnotatedTextField(
        __("Custom URL"),
        description=__(
            "Customize the URL of your project."
            " Use lowercase letters, numbers and dashes only."
            " Including a date is recommended"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(
                max=(
                    Project.__name_length__
                    if Project.__name_length__ is not None
                    else -1
                )
            ),
            forms.validators.ValidName(
                __(
                    "This URL contains unsupported characters. It can contain lowercase"
                    " letters, numbers and hyphens only"
                )
            ),
            AvailableName(),
        ],
        filters=[forms.filters.strip()],
        prefix="https://hasgeek.com/<account>/",
        render_kw={'autocorrect': 'off', 'autocapitalize': 'off'},
    )


class ProjectBannerForm(forms.Form):
    """
    Form for project banner.

    An `account` keyword argument is necessary for the ImgeeField.
    """

    __expects__ = ('account',)
    account: Account

    bg_image = forms.ImgeeField(
        __("Banner image"),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
        filters=nullable_strip_filters,
    )

    def __post_init__(self) -> None:
        """Prepare form for use."""
        self.bg_image.widget_type = 'modal'
        self.bg_image.profile = self.account.name or self.account.buid


@Project.forms('cfp')
class CfpForm(forms.Form):
    """Form for editing instructions for submissions to a project."""

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

    def validate_cfp_end_at(self, field: forms.Field) -> None:
        """Validate closing date to be in the future."""
        if field.data <= utcnow():
            raise forms.validators.StopValidation(
                _("Closing date must be in the future")
            )


@Project.forms('transition')
class ProjectTransitionForm(forms.Form):
    """Form for transitioning a project's state."""

    edit_obj: Project

    transition = forms.SelectField(
        __("Status"), validators=[forms.validators.DataRequired()]
    )

    def __post_init__(self) -> None:
        """Prepare form for use."""
        self.transition.choices = list(self.edit_obj.state.transitions().items())


@Project.forms('cfp_transition')
class ProjectCfpTransitionForm(forms.Form):
    """Form for transitioning a project's submission state."""

    open = forms.BooleanField(
        __("Open submissions"), validators=[forms.validators.InputRequired()]
    )

    def get_open(self, obj: Project) -> bool:
        """Get open state from project."""
        return bool(obj.cfp_state.OPEN)

    def set_open(self, obj: Project) -> None:
        """Set open state and date on project."""
        if self.open.data and not obj.cfp_state.OPEN:
            # Checkbox: yes, but CfP state is not open, so open it
            obj.open_cfp()
        elif not self.open.data and obj.cfp_state.OPEN:
            # Checkbox: no, but CfP state is open, so close it
            obj.close_cfp()
        # No action required in all other cases


@Project.forms('sponsor')
class ProjectSponsorForm(forms.Form):
    """Form to add or edit a sponsor on a project."""

    member = AccountSelectField(
        __("Account"),
        autocomplete_endpoint='/api/1/profile/autocomplete',
        results_key='profile',
        description=__("Choose a sponsor"),
        validators=[forms.validators.DataRequired()],
    )
    label = forms.StringField(
        __("Label"),
        description=__("Optional – Label for sponsor"),
        filters=nullable_strip_filters,
    )
    is_promoted = forms.BooleanField(__("Mark this sponsor as promoted"), default=False)


@SavedProject.forms('main')
class SavedProjectForm(forms.Form):
    """Form to bookmark a project."""

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
    """Form to change RSVP state between Yes, No and Maybe."""

    transition = forms.SelectField(
        __("Status"), validators=[forms.validators.DataRequired()]
    )

    def __post_init__(self) -> None:
        """Prepare form for use."""
        # Usually you need to use an instance's state.transitions to find
        # all the valid transitions for the current state of the instance.
        # But for RSVP, we're showing all the options all the time, so this
        # call is valid. We're also doing this because we want to load the
        # options in the form even without an Rsvp instance.
        self.transition.choices = [
            (transition_name, getattr(Rsvp, transition_name))
            for transition_name in Rsvp.state.transitions
        ]


@Project.forms('rsvp')
class ProjectRegisterForm(forms.Form):
    """Register for a project with an optional custom JSON form."""

    __expects__ = ('schema',)
    schema: dict | None

    form = forms.TextAreaField(
        __("Form"),
        filters=nullable_json_filters,
        validators=[validate_and_convert_json],
    )

    def validate_form(self, field: forms.Field) -> None:
        if not field.data:
            return
        if field.data and not self.schema:
            raise forms.validators.StopValidation(
                _("This registration is not expecting any form fields")
            )
        if self.schema:
            form_keys = set(cast(dict, field.data).keys())
            schema_keys = {i['name'] for i in self.schema['fields']}
            if not form_keys.issubset(schema_keys):
                invalid_keys = form_keys.difference(schema_keys)
                raise forms.validators.StopValidation(
                    _("The form is not expecting these fields: {fields}").format(
                        fields=', '.join(invalid_keys)
                    )
                )


@Project.forms('assign_parent')
class ProjectAssignParentForm(forms.Form):
    """Form to assign a parent project to the project."""

    __expects__ = ('user',)
    user: Account

    parent_project = QuerySelectField(
        __("Assign a parent project"),
        description=__(
            "This is to group related projects. Parent and subprojects will"
            " appear under related events"
        ),
        validators=[forms.validators.Optional()],
        get_label=lambda s: f'{s.account.title}: {s.title}' if s else '',
        allow_blank=True,
        blank_text='None',
    )

    def __post_init__(self) -> None:
        """Prepare form for use."""
        self.parent_project.query = self.user.projects_as_editor
