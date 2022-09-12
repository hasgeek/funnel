"""Test Label forms."""
# pylint: disable=import-outside-toplevel

from werkzeug.datastructures import MultiDict

import pytest


@pytest.mark.usefixtures('app_context')
def test_label_form(forms) -> None:
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
def test_label_form_invalid(forms) -> None:
    form = forms.LabelForm(
        MultiDict({'icon_emoji': "🔟", 'required': False, 'restricted': False}),
        meta={'csrf': False},
    )
    # title is required
    assert not form.validate()
