# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import AvailableName
from ..models import User
from .. import lastuser

__all__ = ['UserGroupForm']


class UserGroupForm(forms.Form):
    name = forms.StringField(__("URL name"), validators=[forms.validators.DataRequired(), forms.validators.ValidName(), AvailableName()])
    title = forms.StringField(__("Title"), validators=[forms.validators.DataRequired()])
    users = forms.UserSelectMultiField(__("Users"), validators=[forms.validators.DataRequired()],
        usermodel=User, lastuser=lastuser)
