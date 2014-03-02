# -*- coding: utf-8 -*-

from coaster.utils import sorted_timezones
from baseframe import __
from baseframe.forms import Form, MarkdownField, ValidName
from baseframe.forms.sqlalchemy import AvailableName
import wtforms
import wtforms.fields.html5
from baseframe.forms import Form

__all__ = ['ProposalSpaceForm']

def set_none(self, field):
    if not field.data:
        field.data = None

class Content(wtforms.Form):
    format = MarkdownField('Format', description=__("Event format, accepted proposals"))
    criteria = MarkdownField('Criteria to submit', description=__("Criteria to submit"))
    panel = MarkdownField('Editorial Panel')
    dates = MarkdownField('Important Dates', description=__("First set of confirmed proposals, Last date to submit, Event Dates, etc"))
    open_source = MarkdownField('Commitment to Open Source')
    title_helper = wtforms.TextField('Helper', description=__("Helper text for the Propose Session link beside title"))

    validate_format = set_none
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
    content = wtforms.fields.FormField(Content)
    timezone = wtforms.SelectField(__("Timezone"),
        description=__("The timezone in which this event occurs"),
        validators=[wtforms.validators.Required()], choices=sorted_timezones(), default=u'UTC')
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

    def validate_date_upto(self, date_upto):
        if self.date_upto.data < self.date.data:
            raise wtforms.ValidationError(_("End date cannot be before Start date"))
