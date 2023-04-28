import json

from funnel import forms

valid_json = json.dumps(
    '''{
            "fields": [    {
            "description": "An explanation for this field",
            "name": "field_name","title": "Field label shown to user",
            "type": "string"},{"name": "has_checked",
            "title": "I accept the terms","type": "boolean"},
            {"choices":
            ["First choice","Second choice","Third choice"],
            "name": "choice","title": "Choose one"}]
            }'''
)

rsvp_excess_json = {
    'choice': 'First choice',
    'field_name': 'Twoflower',
    'has_checked': 'on',
    'company': 'MAANG',
}


def test_valid_boxoffice_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={'register_form_schema': valid_json},
    ):
        form = forms.ProjectBoxofficeForm(meta={'csrf': False})
        assert form.validate() is True


def test_invalid_boxoffice_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={
            'register_form_schema': "This is an invalid json",
        },
    ):
        form = forms.ProjectBoxofficeForm(meta={'csrf': False})
        assert form.validate() is False


def test_valid_json_register_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={'form': '{"field_name":"Vetinari","has_checked":"on"}'},
    ):
        form = forms.ProjectRegisterForm(meta={'csrf': False})
        assert form.validate() is True


def test_invalid_json_register_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={'form': 'This is an invalid json'},
    ):
        form = forms.ProjectRegisterForm(meta={'csrf': False})
        assert form.validate() is False


def test_excess_json_register_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={'form': rsvp_excess_json},
    ):
        form = forms.ProjectRegisterForm(meta={'csrf': False}, schema=valid_json)
        assert form.validate() is False
