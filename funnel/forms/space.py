# -*- coding: utf-8 -*-

import re
from coaster.utils import sorted_timezones
from baseframe import _, __
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import AvailableName, QuerySelectField
from .profile import profile_teams
from ..models import RSVP_STATUS

__all__ = ['ProposalSpaceForm', 'RsvpForm']


valid_color_re = re.compile("^[a-fA-F\d]{6}|[a-fA-F\d]{3}$")


class ProposalSpaceForm(forms.Form):
    name = forms.StringField(__("URL name"), validators=[forms.validators.DataRequired(), forms.ValidName(), AvailableName()])
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    datelocation = forms.StringField(__("Date and Location"), validators=[forms.validators.DataRequired()])
    date = forms.DateField(__("Start date (for sorting)"),
        validators=[forms.validators.DataRequired(__("Enter a valid date in YYYY-MM-DD format"))])
    date_upto = forms.DateField(__("End date (for sorting)"),
        validators=[forms.validators.DataRequired(__("Enter a valid date in YYYY-MM-DD format"))])
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

    def validate_date_upto(self, date_upto):
        if self.date_upto.data < self.date.data:
            raise forms.ValidationError(_("End date cannot be before start date"))

    def validate_bg_color(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")


class RsvpForm(forms.Form):
    status = forms.RadioField("Status", choices=[(k, RSVP_STATUS[k].title) for k in RSVP_STATUS.USER_CHOICES])
