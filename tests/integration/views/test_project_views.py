"""Test project views."""

import pytest

from funnel import forms, models


@pytest.mark.usefixtures('app_context')
def test_new_label_get(client, login, new_user, new_project) -> None:
    login.as_(new_user)
    resp = client.get(new_project.url_for('new_label'))
    label_form = forms.LabelForm(parent=new_project, model=models.Label)
    for field in label_form:
        if field not in ('csrf_token', 'form_nonce'):
            assert field.name in resp.data.decode('utf-8')
