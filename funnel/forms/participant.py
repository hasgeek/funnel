# -*- coding: utf-8 -*-
import os
import wtforms
import baseframe.forms as forms
from baseframe import __
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.widgets import CheckboxInput, ListWidget
from ..models import Participant

__all__ = ['ParticipantForm', 'ParticipantBadgeForm', 'ParticipantContactExchangeForm']


class ParticipantForm(forms.Form):
    fullname = forms.StringField(__("Fullname"), validators=[forms.validators.DataRequired()])
    email = forms.EmailField(__("Email"), validators=[forms.validators.DataRequired(), forms.validators.Length(max=80)])
    phone = forms.StringField(__("Phone number"), validators=[forms.validators.Length(max=80)])
    city = forms.StringField(__("City"), validators=[forms.validators.Length(max=80)])
    company = forms.StringField(__("Company"), validators=[forms.validators.Length(max=80)])
    job_title = forms.StringField(__("Job title"), validators=[forms.validators.Length(max=80)])
    twitter = forms.StringField(__("Twitter"), validators=[forms.validators.Length(max=15)])
    badge_printed = forms.BooleanField(__("Badge is printed"))
    events = QuerySelectMultipleField(__("Events"),
        widget=ListWidget(), option_widget=CheckboxInput(),
        get_label='title',
        validators=[forms.validators.DataRequired(u"Select at least one event")])


class ParticipantBadgeForm(forms.Form):
    choices = [('', "Badge printing status"), ('t', "Printed"), ('f', "Not printed")]
    badge_printed = forms.SelectField("", choices=[(val_title[0], val_title[1]) for val_title in choices])


class ParticipantContactExchangeForm(forms.Form):
    puk = forms.StringField(__("Public key"), validators=[forms.validators.DataRequired()])
    key = forms.StringField(__("Private key"), validators=[forms.validators.DataRequired()])

    class Meta:
        # Disable CSRF as this form will most likely be used over API
        # XXX: Do we need to disable CSRF for this?
        csrf = False

    def validate_key(form, field):
        form.edit_obj = Participant.query.filter_by(puk=form.puk.data, proposal_space=form.edit_parent).first()
        if not form.edit_obj:
            raise forms.ValidationError("Participant not found")
        if form.edit_obj.key != field.data:
            raise forms.ValidationError("Unauthorized contact exchange")
