# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, ValidName
from baseframe.forms.sqlalchemy import AvailableName
import wtforms
import wtforms.fields.html5

__all__ = ['SectionForm']


class SectionForm(Form):
    name = wtforms.TextField(__("URL name"), validators=[wtforms.validators.Required(), ValidName(), AvailableName(scoped=True)])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    description = wtforms.TextAreaField(__("Description"), validators=[wtforms.validators.Required()])
    public = wtforms.BooleanField(__("Public?"), default=True)
