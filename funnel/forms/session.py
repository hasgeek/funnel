# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, MarkdownField
import wtforms

class SessionForm(Form):
	description = MarkdownField(__("Description"), validators=[wtforms.validators.Required()])
	speaker_bio = MarkdownField(__("Speaker bio"), validators=[wtforms.validators.Required()])
	is_break = wtforms.BooleanField(__("This is a break Session"), default=False)
