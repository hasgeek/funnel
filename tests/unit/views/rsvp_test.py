"""Test custom rsvp form views."""

import datetime
import json

from werkzeug.datastructures import MultiDict
import pytest

valid_json = {
    "fields": [
        {
            "description": "An explanation for this field",
            "name": "field_name",
            "title": "Field label shown to user",
            "type": "string",
        },
        {"name": "has_checked", "title": "I accept the terms", "type": "boolean"},
        {
            "choices": ["First choice", "Second choice", "Third choice"],
            "name": "choice",
            "title": "Choose one",
            "type": "select",
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
    'company': 'MAANG',
}


@pytest.fixture(name="project")
def project_fixture(db_session, project_expo2010):
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
def test_valid_json_box_office(
    client, login, user_vetinari, project_expo2010, csrf_token
):
    login.as_(user_vetinari)
    endpoint = project_expo2010.url_for('edit_boxoffice_data')
    rv = client.post(
        endpoint,
        data=MultiDict(
            {
                'org': '',
                'item_collection_id': '',
                'allow_rsvp': True,
                'is_subscription': False,
                'register_button_txt': 'Follow',
                'register_form_schema': json.dumps(valid_json),
                'csrf_token': csrf_token,
            }
        ),
    )
    assert rv.status_code == 303


def test_invalid_json_boxoffice(
    client, login, user_vetinari, project_expo2010, csrf_token
):
    login.as_(user_vetinari)
    endpoint = project_expo2010.url_for('edit_boxoffice_data')
    rv = client.post(
        endpoint,
        data={
            "register_form_schema": 'This is an invalid json',
            'csrf_token': csrf_token,
        },
    )
    assert rv.status_code == 200


def test_valid_json_register(
    client,
    login,
    project,
    user_twoflower,
    csrf_token,
    db_session,
):
    login.as_(user_twoflower)
    endpoint = project.url_for('register')
    rv = client.post(
        endpoint,
        data=json.dumps(
            {
                'form': valid_json_rsvp,
                'csrf_token': csrf_token,
            }
        ),
        headers={'Content-Type': 'application/json'},
    )
    assert rv.status_code == 303
    assert user_twoflower.rsvps.first().form == valid_json_rsvp


def test_invalid_json_register(
    client,
    login,
    project,
    user_twoflower,
    db_session,
):
    login.as_(user_twoflower)
    endpoint = project.url_for('register')
    rv = client.post(
        endpoint,
        data={
            'form': "This is an invalid json",
        },
        headers={'Content-Type': 'application/json'},
    )
    assert rv.status_code == 400