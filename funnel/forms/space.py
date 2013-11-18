# -*- coding: utf-8 -*-

from coaster.utils import sorted_timezones
from baseframe import __
from baseframe.forms import Form, MarkdownField, ValidName
from baseframe.forms.sqlalchemy import AvailableName
from sqlalchemy.orm import validates
import wtforms
import wtforms.fields.html5

__all__ = ['ProposalSpaceForm']


class ProposalSpaceForm(Form):
    name = wtforms.TextField(__("URL name"), validators=[wtforms.validators.Required(), ValidName(), AvailableName()])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    datelocation = wtforms.TextField(__("Date and Location"), validators=[wtforms.validators.Required()])
    date = wtforms.DateField(__("Start Date (for sorting)"),
        validators=[wtforms.validators.Required(__("Enter a valid date in YYYY-MM-DD format"))],
        description=__("In YYYY-MM-DD format"))
    date_upto = wtforms.DateField(__("End Date (for sorting)"),
        validators=[wtforms.validators.Required(__("Enter a valid date in YYYY-MM-DD format"))],
        description=__("In YYYY-MM-DD format"))
    tagline = wtforms.TextField(__("Tagline"), validators=[wtforms.validators.Required()],
        description=__("This is displayed on the card on the homepage"))
    description = MarkdownField(__("Description"), validators=[wtforms.validators.Required()],
        description=__("Instructions for proposers, with Markdown formatting"))
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
            raise wtforms.ValidationError("End Date cannot be before Start Date")
