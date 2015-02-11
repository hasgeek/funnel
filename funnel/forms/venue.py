# -*- coding: utf-8 -*-

from baseframe import __
import baseframe.forms as forms
from baseframe.staticdata import country_codes
from .space import valid_color_re

__all__ = ['VenueForm', 'VenueRoomForm']


class VenueForm(forms.Form):
    title = forms.StringField(__("Name"),
        description=__("Name of the venue"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)])
    description = forms.MarkdownField(__("Description"), description=__("An optional note about the venue"))
    address1 = forms.StringField(__("Address (line 1)"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=160)])
    address2 = forms.StringField(__("Address (line 2)"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=160)])
    city = forms.StringField(__("City"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=30)])
    state = forms.StringField(__("State"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=30)])
    postcode = forms.StringField(__("Post code"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=20)])
    country = forms.SelectField(__("Country"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=2)],
        choices=country_codes, default="IN")
    location = forms.CoordinatesField(__("Location"),
        validators=[forms.validators.Optional(), forms.validators.ValidCoordinates()])


class VenueRoomForm(forms.Form):
    title = forms.StringField(__("Name"), description=__("Name of the room"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)])
    description = forms.MarkdownField(__("Description"), description=__("An optional note about the room"))
    bgcolor = forms.StringField(__("Event Color"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=6)],
        description=__("RGB Color for the event. Enter without the '#'. E.g. CCCCCC."), default=u"CCCCCC")

    def validate_bgcolor(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")
