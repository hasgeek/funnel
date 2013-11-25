# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, MarkdownField
from coaster.utils import nullint
import wtforms

class SessionForm(Form):
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    venue_room_id = wtforms.SelectField(__("Room"), choices=[], coerce=nullint, validators=[wtforms.validators.Optional()])
    description = MarkdownField(__("Description"), validators=[wtforms.validators.Optional()])
    speaker = TextField(__("Speaker"), validators=[wtforms.validators.Optional()])
    speaker_bio = MarkdownField(__("Speaker bio"), validators=[wtforms.validators.Optional()])
    is_break = wtforms.BooleanField(__("This session is a break period"), default=False)
    start = wtforms.HiddenField(__("Start Time"), validators=[wtforms.validators.Required()])
    end = wtforms.HiddenField(__("End Time"), validators=[wtforms.validators.Required()])
