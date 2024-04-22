"""Test Label views."""

import pytest
from flask import Flask

from funnel import models

from ...conftest import LoginFixtureProtocol, TestClient


@pytest.mark.dbcommit
def test_manage_labels_view(
    app: Flask,
    client: TestClient,
    login: LoginFixtureProtocol,
    new_project: models.Project,
    new_user: models.User,
    new_label: models.Label,
    new_main_label: models.Label,
) -> None:
    login.as_(new_user)
    resp = client.get(new_project.url_for('labels'))
    assert "Manage labels" in resp.data.decode('utf-8')
    assert new_label.title in resp.data.decode('utf-8')
    assert new_main_label.title in resp.data.decode('utf-8')


@pytest.mark.dbcommit
def test_edit_option_label_view(
    app: Flask,
    client: TestClient,
    login: LoginFixtureProtocol,
    new_user: models.User,
    new_main_label: models.Label,
) -> None:
    login.as_(new_user)
    opt_label = new_main_label.options[0]
    resp = client.post(opt_label.url_for('edit'), follow_redirects=True)
    assert "Manage labels" in resp.data.decode('utf-8')
    assert "Only main labels can be edited" in resp.data.decode('utf-8')
