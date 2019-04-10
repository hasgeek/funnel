# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from .project import valid_color_re

__all__ = ['LabelsetForm', 'LabelForm']


class LabelsetForm(forms.Form):
    title = forms.StringField(__("Name"),
        description=__("Name of the venue"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)])
    description = forms.MarkdownField(__("Description"), description=__("About Labelset"))


class LabelForm(forms.Form):
    title = forms.StringField(__("Name"), description=__("Name of the room"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)])
    bgcolor = forms.StringField(__("Event Color"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=6)],
        description=__("RGB Color for the event. Enter without the '#'. E.g. CCCCCC."), default=u"CCCCCC")

    def validate_bgcolor(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")
