# -*- coding: utf-8 -*-

import re

from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

from baseframe import __
from baseframe.forms.sqlalchemy import AvailableName
from coaster.utils import sorted_timezones
import baseframe.forms as forms

from ..models import Project, Rsvp

__all__ = [
    'CfpForm',
    'EventForm',
    'ProjectBoxofficeForm',
    'ProjectCfpTransitionForm',
    'ProjectForm',
    'ProjectLivestreamForm',
    'ProjectNameForm',
    'ProjectScheduleTransitionForm',
    'ProjectTransitionForm',
    'RsvpTransitionForm',
    'SavedProjectForm',
    'TicketClientForm',
    'TicketTypeForm',
]

valid_color_re = re.compile(r'^[a-fA-F\d]{6}|[a-fA-F\d]{3}$')

BOXOFFICE_DETAILS_PLACEHOLDER = {"org": "hasgeek", "item_collection_id": ""}


class ProjectForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    location = forms.StringField(
        __("Location"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=50)],
        filters=[forms.filters.strip()],
        description=__("Eg. Bangalore, Mumbai, Pune"),
    )
    tagline = forms.StringField(
        __("Tagline"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)],
        filters=[forms.filters.strip()],
        description=__("One line description of the project"),
    )
    description = forms.MarkdownField(
        __("Project description"),
        validators=[forms.validators.DataRequired()],
        description=__("Landing page contents"),
    )
    timezone = forms.SelectField(
        __("Timezone"),
        description=__("The timezone in which this event occurs"),
        validators=[forms.validators.DataRequired()],
        choices=sorted_timezones(),
        default='UTC',
    )
    bg_image = forms.URLField(
        __("Banner image URL"),
        description=(
            "Banner image for project cards on the homepage. "
            "Resolution should be 1200x675 px. Image size should be around 50KB."
        ),
        validators=[
            forms.validators.Optional(),
            forms.validators.ValidUrl(),
            forms.validators.Length(max=2000),
        ],
    )


class ProjectLivestreamForm(forms.Form):
    livestream_urls = forms.TextListField(
        __("Livestream URLs. One per line."),
        validators=[
            forms.validators.Optional(),
            forms.validators.ForEach(
                [forms.validators.URL(), forms.validators.ValidUrl()]
            ),
        ],
    )


class ProjectNameForm(forms.Form):
    name = forms.AnnotatedTextField(
        __("Custom URL"),
        description=__(
            "Customize the URL of your project. "
            "Use letters, numbers and dashes only. "
            "Including a date is recommended"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Project.__name_length__),
            forms.validators.ValidName(),
            AvailableName(),
        ],
        prefix="https://hasgeek.com/<profile>/",
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )


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
            forms.validators.AllowedIf(
                'cfp_start_at',
                message=__("This requires open time for submissions to be specified"),
            ),
            forms.validators.RequiredIf('cfp_start_at'),
            forms.validators.Optional(),
            forms.validators.GreaterThanEqualTo(
                'cfp_start_at', __("Submissions cannot close before they open")
            ),
        ],
        naive=False,
    )


class ProjectTransitionForm(forms.Form):
    transition = forms.SelectField(
        __("Status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.transition.choices = list(self.edit_obj.state.transitions().items())


class ProjectScheduleTransitionForm(forms.Form):
    schedule_transition = forms.SelectField(
        __("Schedule status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.schedule_transition.choices = list(
            self.edit_obj.schedule_state.transitions().items()
        )


class ProjectCfpTransitionForm(forms.Form):
    cfp_transition = forms.SelectField(
        __("CfP status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.cfp_transition.choices = list(
            self.edit_obj.cfp_state.transitions().items()
        )


class SavedProjectForm(forms.Form):
    save = forms.BooleanField(
        __("Save this project?"), validators=[forms.validators.InputRequired()]
    )
    description = forms.StringField(__("Note to self"))


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


class EventForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    badge_template = forms.URLField(
        __("Badge template URL"),
        description="URL of background image for the badge",
        validators=[forms.validators.Optional(), forms.validators.ValidUrl()],
    )


class TicketClientForm(forms.Form):
    name = forms.StringField(
        __("Name"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    clientid = forms.StringField(
        __("Client id"), validators=[forms.validators.DataRequired()]
    )
    client_eventid = forms.StringField(
        __("Client event id"), validators=[forms.validators.DataRequired()]
    )
    client_secret = forms.StringField(
        __("Client event secret"), validators=[forms.validators.DataRequired()]
    )
    client_access_token = forms.StringField(
        __("Client access token"), validators=[forms.validators.DataRequired()]
    )


class TicketTypeForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    events = QuerySelectMultipleField(
        __("Events"),
        widget=ListWidget(),
        option_widget=CheckboxInput(),
        allow_blank=True,
        get_label='title',
        query_factory=lambda: [],
    )


class ProjectBoxofficeForm(forms.Form):
    boxoffice_data = forms.JsonField(
        __("Ticket client details"), default=BOXOFFICE_DETAILS_PLACEHOLDER
    )
