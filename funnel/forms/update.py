from __future__ import annotations

from baseframe import __, forms

from ..models import Update

__all__ = ['UpdateForm']


@Update.forms('main')
class UpdateForm(forms.Form):
    """Post an update in a project."""

    title = forms.StringField(
        __("Title"),
        validators=[forms.validators.DataRequired()],
        filters=[forms.filters.strip()],
    )
    body = forms.MarkdownField(
        __("Content"),
        validators=[forms.validators.DataRequired()],
        description=__("Markdown formatting is supported"),
    )
    is_pinned = forms.BooleanField(
        __("Pin this update above other updates"), default=False
    )
    is_restricted = forms.BooleanField(
        __("Limit visibility to participants only"), default=False
    )
