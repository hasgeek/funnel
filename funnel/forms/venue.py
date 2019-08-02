# -*- coding: utf-8 -*-

import gettext

import pycountry

from baseframe import __, get_locale
from baseframe.forms.sqlalchemy import QuerySelectField
import baseframe.forms as forms

from .project import valid_color_re

__all__ = ['VenueForm', 'VenuePrimaryForm', 'VenueRoomForm']


class VenueForm(forms.Form):
    title = forms.StringField(
        __("Name"),
        description=__("Name of the venue"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)],
        filters=[forms.filters.strip()],
    )
    description = forms.MarkdownField(
        __("Description"), description=__("An optional note about the venue")
    )
    address1 = forms.StringField(
        __("Address (line 1)"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=160)],
        filters=[forms.filters.strip()],
    )
    address2 = forms.StringField(
        __("Address (line 2)"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=160)],
        filters=[forms.filters.strip()],
    )
    city = forms.StringField(
        __("City"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=30)],
        filters=[forms.filters.strip()],
    )
    state = forms.StringField(
        __("State"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=30)],
        filters=[forms.filters.strip()],
    )
    postcode = forms.StringField(
        __("Post code"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=20)],
        filters=[forms.filters.strip()],
    )
    country = forms.SelectField(
        __("Country"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=2)],
        choices=[],
        default='IN',
    )
    coordinates = forms.CoordinatesField(
        __("Location"),
        description=__("Pick a location on the map"),
        validators=[forms.validators.Optional(), forms.validators.ValidCoordinates()],
    )

    def set_queries(self):
        pycountry_locale = gettext.translation(
            'iso3166-2', pycountry.LOCALES_DIR, languages=[get_locale()]
        )
        countries = [
            (pycountry_locale.gettext(country.name), country.alpha_2)
            for country in pycountry.countries
        ]
        countries.sort()
        self.country.choices = [(code, name) for (name, code) in countries]


class VenueRoomForm(forms.Form):
    title = forms.StringField(
        __("Name"),
        description=__("Name of the room"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=250)],
        filters=[forms.filters.strip()],
    )
    description = forms.MarkdownField(
        __("Description"), description=__("An optional note about the room")
    )
    bgcolor = forms.StringField(
        __("Event Color"),
        validators=[forms.validators.DataRequired(), forms.validators.Length(max=6)],
        description=__("RGB Color for the event. Enter without the '#'. E.g. CCCCCC."),
        default=u"CCCCCC",
    )

    def validate_bgcolor(self, field):
        if not valid_color_re.match(field.data):
            raise forms.ValidationError("Please enter a valid color code")


class VenuePrimaryForm(forms.Form):
    venue = QuerySelectField(
        __("Venue"),
        validators=[forms.validators.DataRequired()],
        get_pk=lambda v: v.suuid,
        get_label='title',
        allow_blank=False,
        widget_attrs={'autocorrect': 'none', 'autocapitalize': 'none'},
    )

    def set_queries(self):
        self.venue.query = self.edit_parent.venues
