# -*- coding: utf-8 -*-

from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

import baseframe.forms as forms
from baseframe import __

__all__ = ['ParticipantForm', 'ParticipantBadgeForm']


class ParticipantForm(forms.Form):
    fullname = forms.StringField(__("Fullname"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()])
    email = forms.EmailField(__("Email"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)],
        filters=[forms.filters.strip()])
    phone = forms.StringField(__("Phone number"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()])
    city = forms.StringField(__("City"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()])
    company = forms.StringField(__("Company"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()])
    job_title = forms.StringField(__("Job title"),
        validators=[forms.validators.Length(max=80)],
        filters=[forms.filters.strip()])
    twitter = forms.StringField(__("Twitter"),
        validators=[forms.validators.Length(max=15)],
        filters=[forms.filters.strip()])
    badge_printed = forms.BooleanField(__("Badge is printed"))
    events = QuerySelectMultipleField(__("Events"),
        widget=ListWidget(), option_widget=CheckboxInput(),
        get_label='title',
        validators=[forms.validators.DataRequired(u"Select at least one event")])


class ParticipantBadgeForm(forms.Form):
    choices = [('', "Badge printing status"), ('t', "Printed"), ('f', "Not printed")]
    badge_printed = forms.SelectField("", choices=[(val_title[0], val_title[1]) for val_title in choices])
