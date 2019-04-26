# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms

__all__ = ['LabelForm', 'LabelOptionForm']


class LabelForm(forms.Form):
    name = forms.StringField("", widget=forms.HiddenInput(), validators=[forms.validators.Optional()])
    title = forms.StringField(__("Label"),
        validators=[forms.validators.DataRequired(__(u"This can’t be empty")), forms.validators.Length(max=250)])
    icon_emoji = forms.StringField("")
    required = forms.BooleanField(__("Make this label mandatory in proposal forms"), default=False,
        description=__("If checked, proposers must select one of the options"))
    restricted = forms.BooleanField(__("Restrict use of this label to editors"), default=False,
        description=__("If checked, only editors and reviewers can apply this label on proposals"))


class LabelOptionForm(forms.Form):
    name = forms.StringField("", widget=forms.HiddenInput(), validators=[forms.validators.Optional()])
    title = forms.StringField(__("Option"),
        validators=[forms.validators.DataRequired(__(u"This can’t be empty")), forms.validators.Length(max=250)])
    icon_emoji = forms.StringField("")
    seq = forms.IntegerField("", widget=forms.HiddenInput())
