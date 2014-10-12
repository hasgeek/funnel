# -*- coding: utf-8 -*-

import re
from coaster.utils import sorted_timezones
from baseframe import _, __
from baseframe.forms import Form, MarkdownField, ValidName
from baseframe.forms.sqlalchemy import AvailableName
import wtforms
import wtforms.fields.html5

__all__ = ['ProposalSpaceForm']


valid_color_re = re.compile("^[a-fA-F\d]{6}|[a-fA-F\d]{3}$")


def set_none(self, field):
    if not field.data:
        field.data = None


class Content(wtforms.Form):
    format = MarkdownField('Format', description=__("Event format"))
    themes = MarkdownField('Themes', description=__("Themes for accepted proposals"))
    criteria = MarkdownField('Criteria to submit', description=__("Criteria to submit"))
    panel = MarkdownField('Editorial Panel')
    dates = MarkdownField('Important Dates', description=__("First set of confirmed proposals, Last date to submit, Event Dates, etc"))
    open_source = MarkdownField('Commitment to Open Source')
    title_helper = wtforms.TextField('Helper', description=__("Helper text for the Propose Session link beside title"))

    validate_format = set_none
    validate_themes = set_none
    validate_criteria = set_none
    validate_panel = set_none
    validate_dates = set_none
    validate_open_source = set_none
    validate_title_helper = set_none


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

    content = wtforms.fields.FormField(Content)

    def validate_date_upto(self, date_upto):
        if self.date_upto.data < self.date.data:
            raise wtforms.ValidationError(_("End date cannot be before Start date"))

    def validate_bg_color(self, field):
        if not valid_color_re.match(field.data):
            raise wtforms.ValidationError("Please enter a valid color code")
