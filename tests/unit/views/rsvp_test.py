"""Test custom rsvp form views."""

import datetime

from werkzeug.datastructures import MultiDict

import pytest

valid_json = '''{
            "fields": [    {
            "description": "An explanation for this field",
            "name": "field_name","title": "Field label shown to user",
            "type": "string"},{"name": "has_checked",
            "title": "I accept the terms","type": "boolean"},
            {"choices":
            ["First choice","Second choice","Third choice"],
            "name": "choice","title": "Choose one","type": "select"}]
            }'''


@pytest.fixture()
def project_expo2010_boxoffice_data(db_session, project_expo2010):
    project_expo2010.start_at = datetime.datetime.now() + datetime.timedelta(days=1)
    project_expo2010.end_at = datetime.datetime.now() + datetime.timedelta(days=2)
    project_expo2010.publish()
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
    db_session.add(project_expo2010)
    db_session.commit()
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
                'register_form_schema': valid_json,
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
    project_expo2010_boxoffice_data,
    user_twoflower,
    csrf_token,
    db_session,
):
    login.as_(user_twoflower)
    endpoint = project_expo2010_boxoffice_data.url_for('register')
    rv = client.post(
        endpoint,
        data=MultiDict(
            {
                'form': '''{
                'field_name': 'Twoflower',
                'has_checked': 'on',
                'choice': 'First choice',
            }''',
                'csrf_token': csrf_token,
            }
        ),
        headers={'Content-Type': 'application/json'},
    )
    print(rv.data)
