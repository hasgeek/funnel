"""Test custom rsvp form views."""
# pylint: disable=redefined-outer-name

import datetime

import pytest
from werkzeug.datastructures import MultiDict

from funnel import models

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


valid_json_rsvp = {
    'field_name': 'Twoflower',
    'has_checked': 'on',
    'choice': 'First choice',
}

rsvp_excess_json = {
    'choice': 'First choice',
    'field_name': 'Twoflower',
    'has_checked': 'on',
    'company': 'MAANG',  # This is extra
}


@pytest.fixture()
def project_expo2010(project_expo2010: models.Project) -> models.Project:
    """Project fixture with a registration form."""
    project_expo2010.start_at = datetime.datetime.now() + datetime.timedelta(days=1)
    project_expo2010.end_at = datetime.datetime.now() + datetime.timedelta(days=2)
    project_expo2010.boxoffice_data = {
        "org": "",
        "is_subscription": False,
        "item_collection_id": "",
        "register_button_txt": "Follow",
        "register_form_schema": {
            "fields": [
                {
                    "name": "field_name",
                    "type": "string",
                    "title": "Field label shown to user",
                },
                {
                    "name": "has_checked",
                    "type": "boolean",
                    "title": "I accept the terms",
                },
                {
                    "name": "choice",
                    "type": "select",
                    "title": "Choose one",
                    "choices": ["First choice", "Second choice", "Third choice"],
                },
            ]
        },
    }
    return project_expo2010


# Organizer side testing
def test_valid_registration_form_schema(
    app,
    client,
    login,
    csrf_token: str,
    user_vetinari: models.User,
    project_expo2010: models.Project,
) -> None:
    """A project can have a registration form provided it is valid JSON."""
    login.as_(user_vetinari)
    endpoint = project_expo2010.url_for('edit_boxoffice_data')
    rv = client.post(
        endpoint,
        data=MultiDict(
            {
                'org': '',
                'item_collection_id': '',
                'rsvp_state': int(models.ProjectRsvpStateEnum.ALL),
                'is_subscription': False,
                'register_button_txt': 'Follow',
                'register_form_schema': app.json.dumps(valid_schema),
                'csrf_token': csrf_token,
            }
        ),
    )
    assert rv.status_code == 303


def test_invalid_registration_form_schema(
    client,
    login,
    csrf_token: str,
    user_vetinari: models.User,
    project_expo2010: models.Project,
) -> None:
    """Registration form schema must be JSON or will be rejected."""
    login.as_(user_vetinari)
    endpoint = project_expo2010.url_for('edit_boxoffice_data')
    rv = client.post(
        endpoint,
        data={
            'register_form_schema': 'This is invalid JSON',
            'csrf_token': csrf_token,
        },
    )
    # Confirm no redirect on success
    assert not 300 <= rv.status_code < 400
    assert 'Invalid JSON' in rv.data.decode()


def test_valid_json_register(
    app,
    client,
    login,
    csrf_token: str,
    user_twoflower: models.User,
    project_expo2010: models.Project,
) -> None:
    """A user can register when the submitted form matches the form schema."""
    login.as_(user_twoflower)
    endpoint = project_expo2010.url_for('register')
    rv = client.post(
        endpoint,
        data=app.json.dumps(
            {
                'form': valid_json_rsvp,
                'csrf_token': csrf_token,
            }
        ),
        headers={'Content-Type': 'application/json'},
    )
    assert rv.status_code == 303
    rsvp = project_expo2010.rsvp_for(user_twoflower)
    assert rsvp is not None
    assert rsvp.form == valid_json_rsvp


def test_valid_encoded_json_register(
    app,
    client,
    login,
    csrf_token: str,
    user_twoflower: models.User,
    project_expo2010: models.Project,
) -> None:
    """A form submission can use non-JSON POST provided the form itself is JSON."""
    login.as_(user_twoflower)
    endpoint = project_expo2010.url_for('register')
    rv = client.post(
        endpoint,
        data={
            'form': app.json.dumps(valid_json_rsvp),
            'csrf_token': csrf_token,
        },
    )
    assert rv.status_code == 303
    rsvp = project_expo2010.rsvp_for(user_twoflower)
    assert rsvp is not None
    assert rsvp.form == valid_json_rsvp


def test_invalid_json_register(
    client, login, user_twoflower: models.User, project_expo2010: models.Project
) -> None:
    """If a registration form is not JSON, it is rejected."""
    login.as_(user_twoflower)
    endpoint = project_expo2010.url_for('register')
    rv = client.post(
        endpoint,
        data="This is not JSON",
        headers={'Content-Type': 'application/json'},
    )
    assert rv.status_code == 400
