"""Test organization admin and project crew membership views."""

import pytest

from funnel import models

from ...conftest import LoginFixtureProtocol, TestClient


@pytest.mark.usefixtures('app_context')
def test_create_new_member(
    client: TestClient,
    login: LoginFixtureProtocol,
    new_user_owner: models.User,
    new_project: models.Project,
) -> None:
    login.as_(new_user_owner)
    # GET request should return a form
    resp = client.get(new_project.url_for('new_member'))
    assert resp.status_code == 200
    assert resp.json is not None
    assert 'form' in resp.json
    assert new_project.url_for('new_member') in resp.json.get('form')

    # FIXME: Can't test new member creation because SelectUserField validation fails
