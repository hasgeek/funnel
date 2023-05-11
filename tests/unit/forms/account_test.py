"""Test account forms."""

from contextlib import nullcontext as does_not_raise
from types import SimpleNamespace

import pytest

from baseframe.forms.validators import StopValidation

from funnel import forms


@pytest.fixture(autouse=True)
def _policy_form_app_context(request, app):
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
    return forms.PasswordPolicyForm(meta={'csrf': False}, edit_user=user)


@pytest.mark.formdata()
def test_password_policy_form_no_data(form) -> None:
    """Test form validation for missing password."""
    assert form.validate() is False


@pytest.mark.formdata({'password': 'weak'})
def test_weak_password(form) -> None:
    """Test weak password validation."""
    assert form.validate() is True
    assert form.is_weak is True
    assert form.password_strength == 1
    assert form.warning == ''
    assert form.suggestions == ['Add another word or two. Uncommon words are better.']


@pytest.mark.formdata({'password': 'rincewind123'})
@pytest.mark.formuser('user_rincewind')
def test_related_password(form) -> None:
    """Password cannot be related to user identifiers (username, email, etc)."""
    assert form.validate() is True
    assert form.edit_user is not None
    assert form.is_weak is True
    assert form.password_strength == 1
    assert form.warning == ''
    assert form.suggestions == ['Add another word or two. Uncommon words are better.']


@pytest.mark.formdata({'password': 'this-is-a-sufficiently-long-password'})
@pytest.mark.formuser('user_rincewind')
def test_okay_password(form) -> None:
    """Long passwords are valid."""
    assert form.validate() is True
    assert form.edit_user is not None
    assert form.is_weak is False
    assert form.password_strength == 4
    assert form.warning == ''
    assert form.suggestions == []


@pytest.mark.remote_data()
def test_pwned_password_validator() -> None:
    """Test the pwned password validator."""
    # Validation success = no return value, no exception
    forms.pwned_password_validator(
        None, SimpleNamespace(data='this is unlikely to be in the breach list')
    )

    with pytest.raises(StopValidation, match='times and is not safe'):
        forms.pwned_password_validator(None, SimpleNamespace(data='123456'))

    with pytest.raises(StopValidation, match='times and is not safe'):
        forms.pwned_password_validator(
            None, SimpleNamespace(data='correct horse battery staple')
        )


# Test for whether the validator handles mangled API output. These hashes are for the
# test password 123456.

# Standard response
resp1 = '''D01CFF3583DDA6607D167C59DCB47012719:3
D032E84B0AEB4E773555C73D6B13BEA7A44:1
D09CA3762AF61E59520943DC26494F8941B:37359195
D0A4AA2E841C50022BB2EA424E43F8FC403:23
D10B1F9D5901978256CE5B2AD832F292D5A:2'''

# Response has spaces around the colon
resp2 = '''D01CFF3583DDA6607D167C59DCB47012719 : 3
D032E84B0AEB4E773555C73D6B13BEA7A44 : 1
D09CA3762AF61E59520943DC26494F8941B : 37359195
D0A4AA2E841C50022BB2EA424E43F8FC403 : 23
D10B1F9D5901978256CE5B2AD832F292D5A : 2'''

# Response is lowercase (and has spaces)
resp3 = '''d01cff3583dda6607d167c59dcb47012719 : 3
d032e84b0aeb4e773555c73d6b13bea7a44 : 1
d09ca3762af61e59520943dc26494f8941b : 37359195
d0a4aa2e841c50022bb2ea424e43f8fc403 : 23
d10b1f9d5901978256ce5b2ad832f292d5a : 2'''

# Response is missing counts (assumed to be 1)
resp4 = '''D01CFF3583DDA6607D167C59DCB47012719
D032E84B0AEB4E773555C73D6B13BEA7A44
D09CA3762AF61E59520943DC26494F8941B
D0A4AA2E841C50022BB2EA424E43F8FC403
D10B1F9D5901978256CE5B2AD832F292D5A'''

# Response has invalid data (not a count)
resp5 = ''''D01CFF3583DDA6607D167C59DCB47012719:a
D032E84B0AEB4E773555C73D6B13BEA7A44:b
D09CA3762AF61E59520943DC26494F8941B:c
D0A4AA2E841C50022BB2EA424E43F8FC403:d
D10B1F9D5901978256CE5B2AD832F292D5A:e'''


# This parametrizing technique is documented at
# https://docs.pytest.org/en/6.2.x/example/parametrize.html
# #parametrizing-conditional-raising
@pytest.mark.parametrize(
    ('text', 'expectation'),
    [
        (resp1, pytest.raises(StopValidation)),
        (resp2, pytest.raises(StopValidation)),
        (resp3, pytest.raises(StopValidation)),
        (resp4, pytest.raises(StopValidation)),
        (resp5, does_not_raise()),
    ],
)
def test_mangled_response_pwned_password_validator(
    requests_mock, text, expectation
) -> None:
    """Test that the validator successfully parses mangled output in the API."""
    requests_mock.get('https://api.pwnedpasswords.com/range/7C4A8', text=text)
    with expectation:
        forms.pwned_password_validator(None, SimpleNamespace(data='123456'))
