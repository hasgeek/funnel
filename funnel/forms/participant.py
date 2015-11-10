# -*- coding: utf-8 -*-
import os
import wtforms
import baseframe.forms as forms
from baseframe import __
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget

__all__ = ['EventParticipantForm', 'ParticipantBadgeForm', 'EventParticipantImportForm']


class ParticipantForm(forms.Form):
    fullname = forms.StringField(__("Full Name"), validators=[forms.validators.DataRequired()])
    email = forms.EmailField(__("Email"), validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)])
    phone = forms.StringField(__("Phone number"), validators=[forms.validators.Length(max=80)])
    city = forms.StringField(__("City"), validators=[forms.validators.Length(max=80)])
    company = forms.StringField(__("Company"), validators=[forms.validators.Length(max=80)])
    job_title = forms.StringField(__("Job Title"), validators=[forms.validators.Length(max=80)])
    twitter = forms.StringField(__("Twitter"), validators=[forms.validators.Length(max=15)])


class EventParticipantForm(ParticipantForm):
    events = QuerySelectMultipleField(__("Events"),
        widget=ListWidget(), option_widget=CheckboxInput(),
        get_label='title',
        validators=[forms.validators.DataRequired(u"Select at least one event")])


# TODO: Move to Baseframe
class ValidFile(object):
    def __init__(self, allowed_exts=[], message=None):
        if not message:
            message = __(u"Please upload a valid file.")
        self.message = message
        self.allowed_exts = allowed_exts

    def __call__(self, form, field):
        ext = os.path.splitext(field.data.filename)[1].strip(".")
        if ext and ext.lower() not in self.allowed_exts:
            raise wtforms.validators.StopValidation(self.message)


class ParticipantImportForm(forms.Form):
    participant_list = forms.FileField(__("Participant list"),
        description=u"Expected headers: name, email, phone (optional), twitter (optional), company (optional)",
        validators=[forms.validators.DataRequired(u"Please upload a valid CSV file"), ValidFile(allowed_exts=['csv'], message=u"Please upload a valid CSV file")])


class EventParticipantImportForm(forms.Form):
    participant_list = forms.FileField(__("Participant list"),
        description=u"Expected headers: name, email, phone (optional), twitter (optional), company (optional)",
        validators=[forms.validators.DataRequired(u"Please upload a valid CSV file"), ValidFile(allowed_exts=['csv'], message=u"Please upload a valid CSV file")])
    events = QuerySelectMultipleField(__("Events"),
        widget=ListWidget(), option_widget=CheckboxInput(),
        get_label='title',
        validators=[forms.validators.DataRequired(u"Select at least one event")])


class ParticipantBadgeForm(forms.Form):
    choices = [('', "Badge printing status"), ('t', "Printed"), ('f', "Not printed")]
    badge_printed = forms.SelectField("", choices=[(val_title[0], val_title[1]) for val_title in choices])
