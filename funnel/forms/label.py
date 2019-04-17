# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from .project import valid_color_re

__all__ = ['LabelForm']


class LabelForm(forms.Form):
    title = forms.StringField(__("Name"), description=__("Name of the label"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)])
    icon_emoji = forms.StringField(__("Icon/Emoji"),
        validators=[forms.validators.Length(max=2)],
        description=__("Emoji to be used for this label for space constrained UI"))
    required = forms.BooleanField(__("Required"), default=False,
        description=__("When required is set, this label must be set for a proposal (e.g. Proposal Type)."))
    restricted = forms.BooleanField(__("Restricted"), default=False,
        description=__("When in restricted mode, only an admin or reviewer can set this label for a proposal (e.g. Proposal Status)."))

    def validate_bgcolor(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")
