# -*- coding: utf-8 -*-

import re
from coaster.utils import sorted_timezones
from baseframe import _, __
from baseframe.forms import Form, MarkdownField, ValidName
from baseframe.forms.sqlalchemy import AvailableName
import wtforms
import wtforms.fields.html5
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from .profile import profile_teams
from ..models import RSVP_ACTION

__all__ = ['ProposalSpaceForm', 'RsvpForm']


valid_color_re = re.compile("^[a-fA-F\d]{6}|[a-fA-F\d]{3}$")


class ProposalSpaceForm(Form):
    name = wtforms.TextField(__("URL name"), validators=[wtforms.validators.Required(), ValidName(), AvailableName()])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    datelocation = wtforms.TextField(__("Date and Location"), validators=[wtforms.validators.Required()])
    date = wtforms.DateField(__("Start date (for sorting)"),
        validators=[wtforms.validators.Required(__("Enter a valid date in YYYY-MM-DD format"))],
        description=__("In YYYY-MM-DD format"))
    date_upto = wtforms.DateField(__("End date (for sorting)"),
        validators=[wtforms.validators.Required(__("Enter a valid date in YYYY-MM-DD format"))],
        description=__("In YYYY-MM-DD format"))
    tagline = wtforms.TextField(__("Tagline"), validators=[wtforms.validators.Required()],
        description=__("This is displayed on the card on the homepage"))
    website = wtforms.fields.html5.URLField(__("Website"),
        validators=[wtforms.validators.Optional()])
    description = MarkdownField(__("Description"), validators=[wtforms.validators.Required()],
        description=__("About Event"))
    timezone = wtforms.SelectField(__("Timezone"),
        description=__("The timezone in which this event occurs"),
        validators=[wtforms.validators.Required()], choices=sorted_timezones(), default=u'UTC')
    bg_image = wtforms.fields.html5.URLField(__("Background image URL"), description=u"Background image for the mobile app",
        validators=[wtforms.validators.Optional()])
    bg_color = wtforms.TextField(__("Background color"),
        description=__("RGB color for the event, shown on the mobile app. Enter without the '#'. E.g. CCCCCC."),
        validators=[wtforms.validators.Optional(), wtforms.validators.length(max=6)],
        default=u"CCCCCC")
    explore_url = wtforms.fields.html5.URLField(__("Explore tab URL"),
        description=__(u"Page containing the explore tab’s contents, for the mobile app"),
        validators=[wtforms.validators.Optional()])

    status = wtforms.SelectField(__("Status"), coerce=int, choices=[
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
    admin_team = QuerySelectField(u"Admin Team", validators=[wtforms.validators.Required(_(u"Please select a team"))],
        query_factory=profile_teams, get_label='title', allow_blank=False,
        description=_(u"The administrators of this proposal space"))
    review_team = QuerySelectField(u"Review Team", validators=[wtforms.validators.Required(_(u"Please select a team"))],
        query_factory=profile_teams, get_label='title', allow_blank=False,
        description=_(u"Reviewers can see contact details of proposers, but can’t change settings"))
    allow_rsvp = wtforms.BooleanField(__("Allow RSVP"))

    def validate_date_upto(self, date_upto):
        if self.date_upto.data < self.date.data:
            raise wtforms.ValidationError(_("End date cannot be before start date"))

    def validate_bg_color(self, field):
        if not valid_color_re.match(field.data):
            raise wtforms.ValidationError("Please enter a valid color code")


class RsvpForm(Form):
    rsvp_action = wtforms.RadioField("rsvp_action", choices=[(key, value['label']) for key, value in RSVP_ACTION.items()])
