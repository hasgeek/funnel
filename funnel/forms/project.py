# -*- coding: utf-8 -*-

import re
from wtforms.widgets import CheckboxInput, ListWidget
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField

from coaster.utils import sorted_timezones
from baseframe import __
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import AvailableName, QuerySelectField

from ..models import RSVP_STATUS, Project

__all__ = [
    'EventForm', 'ProjectForm', 'CfpForm', 'ProjectTransitionForm', 'RsvpForm',
    'SubprojectForm', 'TicketClientForm', 'TicketTypeForm', 'ProjectBoxofficeForm',
    'ProjectScheduleTransitionForm', 'ProjectCfpTransitionForm'
]

valid_color_re = re.compile(r'^[a-fA-F\d]{6}|[a-fA-F\d]{3}$')

BOXOFFICE_DETAILS_PLACEHOLDER = {
    "org": "hasgeek",
    "item_collection_id": ""
}


class ProjectForm(forms.Form):
    name = forms.StringField(__("URL name"), validators=[forms.validators.DataRequired(), forms.ValidName(), AvailableName()])
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    location = forms.StringField(__("Location"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=50)],
        description=__("Eg. Bangalore, Mumbai, Pune"))
    date = forms.DateField(__("Start date"),
        validators=[forms.validators.DataRequired(__("Start date is required"))])
    date_upto = forms.DateField(__("End date"),
        validators=[
            forms.validators.DataRequired(__("End date is required")),
            forms.validators.GreaterThanEqualTo('date', __("End date cannot be before start date"))
            ])
    tagline = forms.StringField(__("Tagline"), validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)],
        description=__("This is displayed on the card on the homepage"))
    website = forms.URLField(__("Website"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=2000)])
    description = forms.MarkdownField(__("Project description"), validators=[forms.validators.DataRequired()],
        description=__("About Event"))
    timezone = forms.SelectField(__("Timezone"),
        description=__("The timezone in which this event occurs"),
        validators=[forms.validators.DataRequired()], choices=sorted_timezones(), default=u'UTC')
    bg_image = forms.URLField(__("Background image URL"), description=u"Background image for the mobile app",
        validators=[forms.validators.Optional(), forms.validators.ValidUrl(), forms.validators.Length(max=2000)])
    bg_color = forms.StringField(__("Background color"),
        description=__("RGB color for the event, shown on the mobile app. Enter without the '#'. E.g. CCCCCC."),
        validators=[forms.validators.Optional(), forms.validators.Length(max=6)],
        default=u"CCCCCC")
    explore_url = forms.URLField(__("Explore tab URL"),
        description=__(u"Page containing the explore tab’s contents, for the mobile app"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=2000)])
    parent_project = QuerySelectField(__(u"Parent project"), get_label='title', allow_blank=True, blank_text=__(u"None"))

    admin_team = QuerySelectField(u"Admin team", validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        get_label='title', allow_blank=False,
        description=__(u"The administrators of this project"))
    review_team = QuerySelectField(u"Review team", validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        get_label='title', allow_blank=False,
        description=__(u"Reviewers can see contact details of proposers, but can’t change settings"))
    checkin_team = QuerySelectField(u"Checkin team", validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        get_label='title', allow_blank=False,
        description=__(u"Team members can check in users at an event"))
    allow_rsvp = forms.BooleanField(__("Allow site visitors to RSVP (login required)"))
    buy_tickets_url = forms.URLField(__("URL to buy tickets"),
        description=__(u"Eg: Explara, Instamojo"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=2000)])

    def set_queries(self):
        profile_teams = self.edit_parent.teams
        self.admin_team.query = profile_teams
        self.review_team.query = profile_teams
        self.checkin_team.query = profile_teams
        if self.edit_obj is None:
            self.parent_project.query = self.edit_parent.projects
        else:
            self.parent_project.query = Project.query.filter(
                Project.profile == self.edit_obj.profile, Project.id != self.edit_obj.id, Project.parent_project == None)  # NOQA

    def validate_bg_color(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")


class CfpForm(forms.Form):
    instructions = forms.MarkdownField(__("Call for proposals"),
        validators=[forms.validators.DataRequired()], default=u'')
    cfp_start_at = forms.DateTimeField(__("Submissions open at"),
        validators=[forms.validators.Optional()])
    cfp_end_at = forms.DateTimeField(__("Submissions close at"),
        validators=[
            forms.validators.AllowedIf('cfp_start_at', message=__("This requires open time for submissions to be specified")),
            forms.validators.RequiredIf('cfp_start_at'), forms.validators.Optional(),
            forms.validators.GreaterThanEqualTo('cfp_start_at', __("Submissions cannot close before they open"))])


class ProjectTransitionForm(forms.Form):
    transition = forms.SelectField(__("Status"), validators=[forms.validators.DataRequired()])

    def set_queries(self):
        self.transition.choices = self.edit_obj.state.transitions().items()


class ProjectScheduleTransitionForm(forms.Form):
    schedule_transition = forms.SelectField(__("Schedule status"), validators=[forms.validators.DataRequired()])

    def set_queries(self):
        self.schedule_transition.choices = self.edit_obj.schedule_state.transitions().items()


class ProjectCfpTransitionForm(forms.Form):
    cfp_transition = forms.SelectField(__("CfP status"), validators=[forms.validators.DataRequired()])

    def set_queries(self):
        self.cfp_transition.choices = self.edit_obj.cfp_state.transitions().items()


class SubprojectForm(ProjectForm):
    inherit_sections = forms.BooleanField(__("Inherit sections from parent project?"), default=True)


class RsvpForm(forms.Form):
    status = forms.RadioField("Status", choices=[(k, RSVP_STATUS[k].title) for k in RSVP_STATUS.USER_CHOICES])


class EventForm(forms.Form):
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    badge_template = forms.URLField(__("Badge template URL"), description=u"URL of background image for the badge",
        validators=[forms.validators.Optional(), forms.validators.ValidUrl(), forms.validators.Length(max=2000)])


class TicketClientForm(forms.Form):
    name = forms.StringField(__("Name"), validators=[forms.validators.DataRequired()])
    clientid = forms.StringField(__("Client id"), validators=[forms.validators.DataRequired()])
    client_eventid = forms.StringField(__("Client event id"), validators=[forms.validators.DataRequired()])
    client_secret = forms.StringField(__("Client event secret"), validators=[forms.validators.DataRequired()])
    client_access_token = forms.StringField(__("Client access token"), validators=[forms.validators.DataRequired()])


class TicketTypeForm(forms.Form):
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    events = QuerySelectMultipleField(__("Events"),
        widget=ListWidget(), option_widget=CheckboxInput(), allow_blank=True, get_label='title', query_factory=lambda: [])


class ProjectBoxofficeForm(forms.Form):
    boxoffice_data = forms.JsonField(__("Ticket client details"), default=BOXOFFICE_DETAILS_PLACEHOLDER)
