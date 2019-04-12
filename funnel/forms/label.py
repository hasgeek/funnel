# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from .project import valid_color_re

__all__ = ['LabelsetForm', 'LabelForm']


class LabelsetForm(forms.Form):
    title = forms.StringField(__("Name"),
        description=__("Name of the labelset"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)])
    description = forms.MarkdownField(__("Description"), description=__("About the labelset"))
    required = forms.BooleanField(__("Required"), default=False,
        description=__("When required is set, this labelset must be set for a proposal (e.g. Proposal Type)."))
    radio_mode = forms.BooleanField(__("Radio mode"), default=False,
        description=__("When in radio mode, only one label within the labelset can be set at a time (e.g. Proposal Type)."))
    restricted = forms.BooleanField(__("Restricted"), default=False,
        description=__("When in restricted mode, only an admin or reviewer can set this labelset for a proposal (e.g. Proposal Status)."))
    archived = forms.BooleanField(__("Archived"), default=False,
        description=__("Once archived, this labelset will not be available for use in future, but the past records will be preserved."))


class LabelForm(forms.Form):
    title = forms.StringField(__("Name"), description=__("Name of the label"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)])
    bgcolor = forms.StringField(__("Label Color"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=6)],
        description=__("RGB Color for the label. Enter without the '#'. E.g. CCCCCC."), default=u"CCCCCC")
    archived = forms.BooleanField(__("Archived"), default=False,
        description=__("Once archived, this label will not be available for use in future, but the past records will be preserved."))
    # We're not going to use icon_emoji until we move to Py3
    # icon_emoji = forms.StringField(__("Icon/Emoji"),
    #     validators=[forms.validators.Length(max=2)],
    #     description=__("Emoji to be used for this label for space constrained UI"))

    def validate_bgcolor(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")
