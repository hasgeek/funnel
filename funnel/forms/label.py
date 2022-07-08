"""Forms for workflow labels."""

from __future__ import annotations

from baseframe import __, forms

from ..models import Label

__all__ = ['LabelForm', 'LabelOptionForm']


@Label.forms('main')
class LabelForm(forms.Form):
    name = forms.StringField(
        "", widget=forms.HiddenInput(), validators=[forms.validators.Optional()]
    )
    title = forms.StringField(
        __("Label"),
        validators=[
            forms.validators.DataRequired(__("This can’t be empty")),
            forms.validators.Length(max=250),
        ],
        filters=[forms.filters.strip()],
    )
    icon_emoji = forms.StringField(
        "", validators=[forms.validators.Optional(), forms.validators.IsEmoji()]
    )
    required = forms.BooleanField(
        __("Make this label mandatory in submission forms"),
        default=False,
        description=__("If checked, submitters must select one of the options"),
    )
    restricted = forms.BooleanField(
        __("Restrict use of this label to editors"),
        default=False,
        description=__(
            "If checked, only editors and reviewers can apply this label on proposals"
        ),
    )


@Label.forms('option')
class LabelOptionForm(forms.Form):
    name = forms.StringField(
        "", widget=forms.HiddenInput(), validators=[forms.validators.Optional()]
    )
    title = forms.StringField(
        __("Option"),
        validators=[
            forms.validators.DataRequired(__("This can’t be empty")),
            forms.validators.Length(max=250),
        ],
        filters=[forms.filters.strip()],
    )
    icon_emoji = forms.StringField(
        "", validators=[forms.validators.Optional(), forms.validators.IsEmoji()]
    )
    seq = forms.IntegerField("", widget=forms.HiddenInput())
