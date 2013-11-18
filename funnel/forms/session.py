# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, MarkdownField
import wtforms

class SessionForm(Form):
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    venue_room_id = wtforms.SelectField(__("Room"), choices=[], coerce=int)
    description = MarkdownField(__("Description"), validators=[wtforms.validators.Required()])
    speaker_bio = MarkdownField(__("Speaker bio"), validators=[wtforms.validators.Required()])
    is_break = wtforms.BooleanField(__("This is a break Session"), default=False)
    start = wtforms.HiddenField(__("Start Time"), validators=[wtforms.validators.Required()])
    end = wtforms.HiddenField(__("End Time"), validators=[wtforms.validators.Required()])
