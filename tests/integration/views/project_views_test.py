"""Test project views."""

import pytest

from funnel import forms, models

from ...conftest import LoginFixtureProtocol, TestClient


@pytest.mark.usefixtures('app_context')
def test_new_label_get(
    client: TestClient,
    login: LoginFixtureProtocol,
    new_user: models.User,
    new_project: models.Project,
) -> None:
    login.as_(new_user)
    resp = client.get(new_project.url_for('new_label'))
    label_form = forms.LabelForm(parent=new_project, model=models.Label)
    for field in label_form:
        if field != 'csrf_token':
            assert field.name in resp.data.decode('utf-8')
