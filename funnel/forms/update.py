"""Forms for project updates."""

from __future__ import annotations

from baseframe import __, forms

from ..models import VISIBILITY_STATE, Update

__all__ = ['UpdateForm', 'UpdatePinForm']


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
    visibility = forms.RadioField(
        __("Who gets this update?"),
        description=__("This can’t be changed after publishing the update"),
        default=VISIBILITY_STATE[VISIBILITY_STATE.PUBLIC].name,
        choices=[
            (
                VISIBILITY_STATE[VISIBILITY_STATE.PUBLIC].name,
                __("Public; account followers will be notified"),
            ),
            (
                VISIBILITY_STATE[VISIBILITY_STATE.MEMBERS].name,
                __("Only account members"),
            ),
            (
                VISIBILITY_STATE[VISIBILITY_STATE.PARTICIPANTS].name,
                __("Only project participants"),
            ),
        ],
    )


@Update.forms('pin')
class UpdatePinForm(forms.Form):
    """Pin an update in a project."""

    is_pinned = forms.BooleanField(
        __("Pin this update above other updates"), default=False
    )
