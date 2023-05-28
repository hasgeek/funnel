"""Test custom rsvp forms."""

import json

from funnel import forms

valid_schema = {
    'fields': [
        {
            'description': "An explanation for this field",
            'name': 'field_name',
            'title': "Field label shown to user",
            'type': 'string',
        },
        {
            'name': 'has_checked',
            'title': "I accept the terms",
            'type': 'boolean',
        },
        {
            'name': 'choice',
            'title': "Choose one",
            'choices': ["First choice", "Second choice", "Third choice"],
        },
    ]
}

rsvp_excess_json = {
    'choice': 'First choice',
    'field_name': 'Twoflower',
    'has_checked': 'on',
    'company': 'MAANG',  # This is not in the form
}


def test_valid_boxoffice_form(app) -> None:
    """Valid schema is accepted by the schema form validator."""
    with app.test_request_context(
        method='POST',
        data={'register_form_schema': json.dumps(valid_schema)},
    ):
        form = forms.ProjectBoxofficeForm(meta={'csrf': False})
        assert form.validate() is True


def test_invalid_boxoffice_form(app) -> None:
    """Invalid schema is rejected by the schema form validator."""
    with app.test_request_context(
        method='POST',
        data={
            'register_form_schema': "This is an invalid json",
        },
    ):
        form = forms.ProjectBoxofficeForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.errors == {'register_form_schema': ['Invalid JSON']}


def test_valid_json_register_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={'form': '{"field_name":"Vetinari","has_checked":"on"}'},
    ):
        form = forms.ProjectRegisterForm(meta={'csrf': False}, schema=valid_schema)
        assert form.validate() is True


def test_invalid_json_register_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={'form': 'This is an invalid json'},
    ):
        form = forms.ProjectRegisterForm(meta={'csrf': False}, schema=valid_schema)
        assert form.validate() is False
        assert 'form' in form.errors  # Field named 'form' has an error
        assert form.form.errors == ['Invalid JSON']


def test_excess_json_register_form(app) -> None:
    with app.test_request_context(
        method='POST',
        data={'form': json.dumps(rsvp_excess_json)},
    ):
        form = forms.ProjectRegisterForm(meta={'csrf': False}, schema=valid_schema)
        assert form.validate() is False
        assert 'form' in form.errors  # Field named 'form' has an error
        assert form.form.errors == ["The form is not expecting these fields: company"]
