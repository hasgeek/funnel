"""Test Label forms."""

from werkzeug.datastructures import MultiDict

import pytest

from funnel.forms import LabelForm


@pytest.mark.usefixtures('app')
def test_label_form() -> None:
    form = LabelForm(
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


@pytest.mark.usefixtures('app')
def test_label_form_invalid() -> None:
    form = LabelForm(
        MultiDict({'icon_emoji': "🔟", 'required': False, 'restricted': False}),
        meta={'csrf': False},
    )
    # title is required
    assert not form.validate()
