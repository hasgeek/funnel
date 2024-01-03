"""Test Label views."""

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import scoped_session

from funnel import models

from ...conftest import LoginFixtureProtocol


@pytest.mark.dbcommit()
def test_manage_labels_view(
    app: Flask,
    client: FlaskClient,
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


@pytest.mark.dbcommit()
def test_edit_option_label_view(
    app: Flask,
    client: FlaskClient,
    login: LoginFixtureProtocol,
    new_user: models.User,
    new_main_label: models.Label,
) -> None:
    login.as_(new_user)
    opt_label = new_main_label.options[0]
    resp = client.post(opt_label.url_for('edit'), follow_redirects=True)
    assert "Manage labels" in resp.data.decode('utf-8')
    assert "Only main labels can be edited" in resp.data.decode('utf-8')


@pytest.mark.xfail(reason="Broken after Flask-SQLAlchemy 3.0, unclear why")  # FIXME
def test_main_label_delete(
    db_session: scoped_session,
    client: FlaskClient,
    login: LoginFixtureProtocol,
    new_user: models.User,
    new_label: models.Label,
) -> None:
    login.as_(new_user)
    resp = client.post(new_label.url_for('delete'), follow_redirects=True)
    assert "Manage labels" in resp.data.decode('utf-8')
    assert "The label has been deleted" in resp.data.decode('utf-8')
    label = db_session.get(models.Label, new_label.id)
    assert label is None


@pytest.mark.xfail(reason="Broken after Flask-SQLAlchemy 3.0, unclear why")  # FIXME
def test_optioned_label_delete(
    db_session: scoped_session,
    client: FlaskClient,
    login: LoginFixtureProtocol,
    new_user: models.User,
    new_main_label: models.Label,
) -> None:
    login.as_(new_user)
    label_a1 = new_main_label.options[0]
    label_a2 = new_main_label.options[1]

    # let's delete the main optioned label
    resp = client.post(new_main_label.url_for('delete'), follow_redirects=True)
    assert "Manage labels" in resp.data.decode('utf-8')
    assert "The label has been deleted" in resp.data.decode('utf-8')
    mlabel = db_session.get(models.Label, new_main_label.id)
    assert mlabel is None

    # so the option labels should have been deleted as well
    for olabel in [label_a1, label_a2]:
        assert models.Label.query.get(olabel.id) is None
