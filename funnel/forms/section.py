# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import AvailableName

__all__ = ['SectionForm']


class SectionForm(forms.Form):
    name = forms.StringField(__("URL name"), validators=[forms.validators.DataRequired(), forms.ValidName(), AvailableName()])
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    description = forms.TextAreaField(__("Description"), validators=[forms.validators.DataRequired()])
    public = forms.BooleanField(__("Public?"), default=True)
