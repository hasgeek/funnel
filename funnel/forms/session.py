# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from coaster.utils import nullint


class SessionForm(forms.Form):
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    venue_room_id = forms.SelectField(__("Room"), choices=[], coerce=nullint, validators=[forms.validators.Optional()])
    description = forms.MarkdownField(__("Description"), validators=[forms.validators.Optional()])
    speaker = forms.StringField(__("Speaker"), validators=[forms.validators.Optional()])
    speaker_bio = forms.MarkdownField(__("Speaker bio"), validators=[forms.validators.Optional()])
    is_break = forms.BooleanField(__("This session is a break period"), default=False)
    start = forms.HiddenField(__("Start Time"), validators=[forms.validators.DataRequired()])
    end = forms.HiddenField(__("End Time"), validators=[forms.validators.DataRequired()])
