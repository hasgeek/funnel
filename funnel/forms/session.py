from __future__ import annotations

from baseframe import __
from coaster.utils import nullint
import baseframe.forms as forms

from ..models import SavedSession, Session
from .helpers import image_url_validator, nullable_strip_filters

__all__ = ['SavedSessionForm', 'SessionForm']


@Session.forms('main')
class SessionForm(forms.Form):
    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    venue_room_id = forms.SelectField(
        __("Room"), choices=[], coerce=nullint, validators=[forms.validators.Optional()]
    )
    description = forms.MarkdownField(
        __("Description"), validators=[forms.validators.Optional()]
    )
    speaker = forms.StringField(
        __("Speaker"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=200)],
        filters=[forms.filters.strip()],
    )
    banner_image_url = forms.URLField(
        __("Banner image URL"),
        description=__(
            "From images.hasgeek.com, with 16:9 aspect ratio."
            " Should be < 50 kB in size"
        ),
        validators=[
            forms.validators.Optional(),
            forms.validators.Length(max=2000),
            image_url_validator(),
        ],
        filters=nullable_strip_filters,
    )
    is_break = forms.BooleanField(__("This session is a break period"), default=False)
    featured = forms.BooleanField(__("This is a featured session"), default=False)
    start_at = forms.HiddenField(
        __("Start Time"), validators=[forms.validators.DataRequired()]
    )
    end_at = forms.HiddenField(
        __("End Time"), validators=[forms.validators.DataRequired()]
    )
    video_url = forms.StringField(
        __("Video URL"),
        description=__("URL of the uploaded video after the session is over"),
        validators=[
            forms.validators.Optional(),
            forms.validators.ValidUrl(),
            forms.validators.Length(max=2000),
        ],
        filters=nullable_strip_filters,
    )


@SavedSession.forms('main')
class SavedSessionForm(forms.Form):
    save = forms.BooleanField(
        __("Save this session?"), validators=[forms.validators.InputRequired()]
    )
    description = forms.StringField(__("Note to self"))
