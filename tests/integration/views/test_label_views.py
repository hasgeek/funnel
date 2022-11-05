"""Test Label views."""
# pylint: disable=too-many-arguments

import pytest

from funnel import models


@pytest.mark.dbcommit()
def test_manage_labels_view(
    app, client, login, new_project, new_user, new_label, new_main_label
) -> None:
    login.as_(new_user)
    with app.app_context():
        resp = client.get(new_project.url_for('labels'))
    assert "Manage labels" in resp.data.decode('utf-8')
    assert new_label.title in resp.data.decode('utf-8')
    assert new_main_label.title in resp.data.decode('utf-8')


@pytest.mark.dbcommit()
def test_edit_option_label_view(app, client, login, new_user, new_main_label) -> None:
    login.as_(new_user)
    opt_label = new_main_label.options[0]
    with app.app_context():
        resp = client.post(opt_label.url_for('edit'), follow_redirects=True)
    assert "Manage labels" in resp.data.decode('utf-8')
    assert "Only main labels can be edited" in resp.data.decode('utf-8')


# Separate class because the ``new_label`` fixture has a class scope.
# If we delete it in any other test classes, it'll mess with other
# tests in those classes.


@pytest.mark.dbcommit()
def test_main_label_delete(app, client, login, new_user, new_label) -> None:
    login.as_(new_user)
    with app.app_context():
        resp = client.post(new_label.url_for('delete'), follow_redirects=True)
    assert "Manage labels" in resp.data.decode('utf-8')
    assert "The label has been deleted" in resp.data.decode('utf-8')
    label = models.Label.query.get(new_label.id)
    assert label is None


@pytest.mark.dbcommit()
def test_optioned_label_delete(app, client, login, new_user, new_main_label) -> None:
    login.as_(new_user)
    label_a1 = new_main_label.options[0]
    label_a2 = new_main_label.options[1]

    # let's delete the main optioned label
    with app.app_context():
        resp = client.post(new_main_label.url_for('delete'), follow_redirects=True)
    assert "Manage labels" in resp.data.decode('utf-8')
    assert "The label has been deleted" in resp.data.decode('utf-8')
    mlabel = models.Label.query.get(new_main_label.id)
    assert mlabel is None

    # so the option labels should have been deleted as well
    for olabel in [label_a1, label_a2]:
        assert models.Label.query.get(olabel.id) is None
