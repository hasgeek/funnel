"""Test project views."""

from funnel.forms import LabelForm
from funnel.models import Label


def test_new_label_get(client, login, new_user, new_project) -> None:
    login.as_(new_user)
    resp = client.get(new_project.url_for('new_label'))
    label_form = LabelForm(parent=new_project, model=Label)
    for field in label_form:
        if field not in ('csrf_token', 'form_nonce'):
            assert field.name in resp.data.decode('utf-8')
