# -*- coding: utf-8 -*-

import re

from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

from baseframe import __
from baseframe.forms.sqlalchemy import AvailableName, QuerySelectField
from coaster.utils import sorted_timezones
import baseframe.forms as forms

from ..models import Project, Rsvp

__all__ = [
    'CfpForm',
    'EventForm',
    'ProjectBoxofficeForm',
    'ProjectCfpTransitionForm',
    'ProjectForm',
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
    name = forms.StringField(
        __("URL name"),
        validators=[
            forms.validators.DataRequired(),
            forms.ValidName(),
            AvailableName(),
        ],
    )
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
        description=__("This is displayed on the card on the homepage"),
    )
    website = forms.URLField(
        __("Website"),
        validators=[
            forms.validators.Optional(),
            forms.validators.URL(),
            forms.validators.ValidUrl(),
        ],
    )
    description = forms.MarkdownField(
        __("Project description"),
        validators=[forms.validators.DataRequired()],
        description=__("About the project"),
    )
    timezone = forms.SelectField(
        __("Timezone"),
        description=__("The timezone in which this event occurs"),
        validators=[forms.validators.DataRequired()],
        choices=sorted_timezones(),
        default=u'UTC',
    )
    bg_image = forms.URLField(
        __("Banner image URL"),
        description=u"Banner image for project cards on the homepage",
        validators=[
            forms.validators.Optional(),
            forms.validators.ValidUrl(),
            forms.validators.Length(max=2000),
        ],
    )
    bg_color = forms.StringField(
        __("Background color"),
        description=__(
            "RGB color for the project. Enter without the '#'. E.g. CCCCCC."
        ),
        validators=[forms.validators.Optional(), forms.validators.Length(max=6)],
        default=u"CCCCCC",
    )
    explore_url = forms.URLField(
        __("Explore tab URL"),
        description=__(
            u"Page containing the explore tab’s contents, for the mobile app"
        ),
        validators=[
            forms.validators.Optional(),
            forms.validators.URL(),
            forms.validators.ValidUrl(),
        ],
    )
    parent_project = QuerySelectField(
        __(u"Parent project"),
        get_label='title',
        allow_blank=True,
        blank_text=__(u"None"),
    )

    admin_team = QuerySelectField(
        u"Admin team",
        validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        get_label='title',
        allow_blank=False,
        description=__(u"The administrators of this project"),
    )
    review_team = QuerySelectField(
        u"Review team",
        validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        get_label='title',
        allow_blank=False,
        description=__(
            u"Reviewers can see contact details of proposers, but can’t change settings"
        ),
    )
    checkin_team = QuerySelectField(
        u"Checkin team",
        validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        get_label='title',
        allow_blank=False,
        description=__(u"Team members can check in users at an event"),
    )
    allow_rsvp = forms.BooleanField(__("Allow site visitors to RSVP (login required)"))
    buy_tickets_url = forms.URLField(
        __("URL to buy tickets"),
        description=__(u"Eg: Explara, Instamojo"),
        validators=[
            forms.validators.Optional(),
            forms.validators.URL(),
            forms.validators.ValidUrl(),
            forms.validators.Length(max=2000),
        ],
    )

    def set_queries(self):
        profile_teams = self.edit_parent.teams
        self.admin_team.query = profile_teams
        self.review_team.query = profile_teams
        self.checkin_team.query = profile_teams
        if self.edit_obj is None:
            self.parent_project.query = self.edit_parent.projects
        else:
            self.parent_project.query = Project.query.filter(
                Project.profile == self.edit_obj.profile,
                Project.id != self.edit_obj.id,
                Project.parent_project == None,
            )  # NOQA

    def validate_bg_color(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")


class CfpForm(forms.Form):
    instructions = forms.MarkdownField(
        __("Call for proposals"),
        validators=[forms.validators.DataRequired()],
        default=u'',
    )
    cfp_start_at = forms.DateTimeField(
        __("Submissions open at"), validators=[forms.validators.Optional()], naive=False
    )
    cfp_end_at = forms.DateTimeField(
        __("Submissions close at"),
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
        self.transition.choices = self.edit_obj.state.transitions().items()


class ProjectScheduleTransitionForm(forms.Form):
    schedule_transition = forms.SelectField(
        __("Schedule status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.schedule_transition.choices = (
            self.edit_obj.schedule_state.transitions().items()
        )


class ProjectCfpTransitionForm(forms.Form):
    cfp_transition = forms.SelectField(
        __("CfP status"), validators=[forms.validators.DataRequired()]
    )

    def set_queries(self):
        self.cfp_transition.choices = self.edit_obj.cfp_state.transitions().items()


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
        description=u"URL of background image for the badge",
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
