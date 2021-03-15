from werkzeug.datastructures import MultiDict

from funnel.forms import LabelForm


def test_label_form():
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


def test_label_form_invalid():
    form = LabelForm(
        MultiDict({'icon_emoji': "🔟", 'required': False, 'restricted': False}),
        meta={'csrf': False},
    )
    # title is required
    assert not form.validate()
