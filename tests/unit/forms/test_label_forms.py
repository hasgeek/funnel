"""Test Label forms."""

from werkzeug.datastructures import MultiDict

import pytest

from funnel import forms


@pytest.mark.usefixtures('app_context')
def test_label_form() -> None:
    form = forms.LabelForm(
        MultiDict(
            {
                'title': "Test label title",
                'icon_emoji': "🔟",
                'required': False,
                'restricted': False,
            }
        ),
        meta={'csrf': False},
    )
    assert form.validate()


@pytest.mark.usefixtures('app_context')
def test_label_form_invalid() -> None:
    form = forms.LabelForm(
        MultiDict({'icon_emoji': "🔟", 'required': False, 'restricted': False}),
        meta={'csrf': False},
    )
    # title is required
    assert not form.validate()
