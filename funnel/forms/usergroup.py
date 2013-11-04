# -*- coding: utf-8 -*-

from baseframe import __
from baseframe.forms import Form, ValidName
from baseframe.forms.sqlalchemy import AvailableName
import wtforms
import wtforms.fields.html5

__all__ = ['UserGroupForm']


class UserGroupForm(Form):
    name = wtforms.TextField(__("URL name"), validators=[wtforms.validators.Required(), ValidName(), AvailableName(scoped=True)])
    title = wtforms.TextField(__("Title"), validators=[wtforms.validators.Required()])
    users = wtforms.TextAreaField(__("Users"), validators=[wtforms.validators.Required()],
        description=__("Usernames or email addresses, one per line"))
