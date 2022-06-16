"""Test account forms."""

import pytest

from funnel import app
from funnel.forms import PasswordPolicyForm


@pytest.fixture(autouse=True)
def _policy_form_app_context(request):
    """Create a POST request context with form data."""
    data = {}
    for mark in request.node.iter_markers('formdata'):
        data.update(dict(*mark.args, **mark.kwargs))

    with app.test_request_context(method='POST', data=data):
        yield


@pytest.fixture()
def form(request):
    """Form fixture."""
    user = None
    for mark in request.node.iter_markers('formuser'):
        if mark.args:
            if user is not None:
                pytest.fail("Only one formuser can be mentioned in marks.")
            user = request.getfixturevalue(mark.args[0])
    return PasswordPolicyForm(meta={'csrf': False}, edit_user=user)


@pytest.mark.formdata()
def test_password_policy_form_no_data(form):
    """Test form validation for missing password."""
    assert form.validate() is False


@pytest.mark.formdata({'password': 'weak'})
def test_weak_password(form):
    """Test weak password validation."""
    assert form.validate() is True
    assert form.is_weak is True
    assert form.password_strength == 1
    assert form.warning == ''
    assert form.suggestions == ['Add another word or two. Uncommon words are better.']


@pytest.mark.formdata({'password': 'rincewind123'})
@pytest.mark.formuser('user_rincewind')
def test_related_password(form):
    """Password cannot be related to user identifiers (username, email, etc)."""
    assert form.validate() is True
    assert form.edit_user is not None
    assert form.is_weak is True
    assert form.password_strength == 1
    assert form.warning == ''
    assert form.suggestions == ['Add another word or two. Uncommon words are better.']


@pytest.mark.formdata({'password': 'this-is-a-sufficiently-long-password'})
@pytest.mark.formuser('user_rincewind')
def test_okay_password(form):
    """Long passwords are valid."""
    assert form.validate() is True
    assert form.edit_user is not None
    assert form.is_weak is False
    assert form.password_strength == 4
    assert form.warning == ''
    assert form.suggestions == []
