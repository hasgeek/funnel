# -*- coding: utf-8 -*-

import re
from coaster.utils import sorted_timezones
from wtforms.widgets import CheckboxInput, ListWidget
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from baseframe import _, __
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import AvailableName, QuerySelectField
from .profile import profile_teams
from ..models import RSVP_STATUS

__all__ = ['ProposalSpaceForm', 'ProposalSubspaceForm', 'RsvpForm', 'EventForm', 'TicketTypeForm', 'TicketClientForm']


valid_color_re = re.compile("^[a-fA-F\d]{6}|[a-fA-F\d]{3}$")


class ProposalSpaceForm(forms.Form):
    name = forms.StringField(__("URL name"), validators=[forms.validators.DataRequired(), forms.ValidName(), AvailableName()])
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    datelocation = forms.StringField(__("Date and Location"), validators=[forms.validators.DataRequired(), forms.validators.Length(max=50)])
    date = forms.DateField(__("Start date (for sorting)"),
        validators=[forms.validators.DataRequired(__("This field is required"))])
    date_upto = forms.DateField(__("End date (for sorting)"),
        validators=[forms.validators.DataRequired(__("This is required"))])
    tagline = forms.StringField(__("Tagline"), validators=[forms.validators.DataRequired()],
        description=__("This is displayed on the card on the homepage"))
    website = forms.URLField(__("Website"),
        validators=[forms.validators.Optional()])
    description = forms.MarkdownField(__("Description"), validators=[forms.validators.DataRequired()],
        description=__("About Event"))
    timezone = forms.SelectField(__("Timezone"),
        description=__("The timezone in which this event occurs"),
        validators=[forms.validators.DataRequired()], choices=sorted_timezones(), default=u'UTC')
    bg_image = forms.URLField(__("Background image URL"), description=u"Background image for the mobile app",
        validators=[forms.validators.Optional()])
    bg_color = forms.StringField(__("Background color"),
        description=__("RGB color for the event, shown on the mobile app. Enter without the '#'. E.g. CCCCCC."),
        validators=[forms.validators.Optional(), forms.validators.Length(max=6)],
        default=u"CCCCCC")
    explore_url = forms.URLField(__("Explore tab URL"),
        description=__(u"Page containing the explore tab’s contents, for the mobile app"),
        validators=[forms.validators.Optional()])
    parent_space = QuerySelectField(__(u"Parent space"), get_label='title', allow_blank=True, blank_text=__(u"None"))

    status = forms.SelectField(__("Status"), coerce=int, choices=[
        (0, __("Draft")),
        (1, __("Open")),
        (2, __("Voting")),
        (3, __("Jury selection")),
        (4, __("Feedback")),
        (5, __("Closed")),
        (6, __("Withdrawn")),
        ],
        description=__(u"Proposals can only be submitted in the “Open” state. "
            u"“Closed” and “Withdrawn” are hidden from homepage"))
    admin_team = QuerySelectField(u"Admin Team", validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        query_factory=profile_teams, get_label='title', allow_blank=False,
        description=__(u"The administrators of this proposal space"))
    review_team = QuerySelectField(u"Review Team", validators=[forms.validators.DataRequired(__(u"Please select a team"))],
        query_factory=profile_teams, get_label='title', allow_blank=False,
        description=__(u"Reviewers can see contact details of proposers, but can’t change settings"))
    allow_rsvp = forms.BooleanField(__("Allow site visitors to RSVP (login required)"))
    buy_tickets_url = forms.URLField(__("URL to buy tickets"),
        description=__(u"Eg: Explara, Instamojo"),
        validators=[forms.validators.Optional()])

    def validate_date_upto(self, date_upto):
        if self.date_upto.data < self.date.data:
            raise forms.ValidationError(_("End date cannot be before start date"))

    def validate_bg_color(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")


class ProposalSubspaceForm(ProposalSpaceForm):
    inherit_sections = forms.BooleanField(__("Inherit sections from parent space?"), default=True)


class RsvpForm(forms.Form):
    status = forms.RadioField("Status", choices=[(k, RSVP_STATUS[k].title) for k in RSVP_STATUS.USER_CHOICES])


class EventForm(forms.Form):
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])


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
