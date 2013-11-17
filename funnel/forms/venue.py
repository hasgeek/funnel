# -*- coding: utf-8 -*-

import wtforms
import re
from baseframe import __
from baseframe.forms import Form, MarkdownField
from baseframe.staticdata import country_codes


__all__ = ['VenueForm', 'VenueRoomForm']


class VenueForm(Form):
    title = wtforms.TextField(__("Name"),
        description=__("Name of the venue"),
        validators=[wtforms.validators.Required(), wtforms.validators.length(max=250)])
    description = MarkdownField(__("Description"), description=__("An optional note about the venue"))
    address1 = wtforms.TextField(__("Address (line 1)"),
        validators=[wtforms.validators.Optional(), wtforms.validators.length(max=160)])
    address2 = wtforms.TextField(__("Address (line 2)"),
        validators=[wtforms.validators.Optional(), wtforms.validators.length(max=160)])
    city = wtforms.TextField(__("City"),
        validators=[wtforms.validators.Optional(), wtforms.validators.length(max=30)])
    state = wtforms.TextField(__("State"),
        validators=[wtforms.validators.Optional(), wtforms.validators.length(max=30)])
    postcode = wtforms.TextField(__("Post code"),
        validators=[wtforms.validators.Optional(), wtforms.validators.length(max=20)])
    country = wtforms.SelectField(__("Country"),
        validators=[wtforms.validators.Optional(), wtforms.validators.length(max=2)],
        choices=country_codes, default="IN")
    latitude = wtforms.DecimalField(__("Latitude"), places=None,
        validators=[wtforms.validators.Optional(), wtforms.validators.NumberRange(-90, 90)])
    longitude = wtforms.DecimalField(__("Longitude"), places=None,
        validators=[wtforms.validators.Optional(), wtforms.validators.NumberRange(-180, 180)])


class VenueRoomForm(Form):
    title = wtforms.TextField(__("Name"), description=__("Name of the room"),
        validators=[wtforms.validators.Required(), wtforms.validators.length(max=250)])
    description = MarkdownField(__("Description"), description=__("An optional note about the room"))
    bgcolor = wtforms.TextField(__("Event Color"), validators=[wtforms.validators.Required(), wtforms.validators.length(max=6)],
        description=__("RGB Color for the event. Enter without the '#'. E.g. CCCCCC."), default=u"CCCCCC")

    def validate_bgcolor(self, bgcolor):
        valid = re.compile("^[a-fA-F\d]{6}|[a-fA-F\d]{3}$")
        if not valid.match(bgcolor.data):
            raise wtforms.ValidationError("Please enter a valid color code")