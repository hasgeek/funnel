"""Test main login form for password and OTP flows."""

# pylint: disable=redefined-outer-name

import pytest
from flask import Flask

from funnel import forms, models

from ...conftest import scoped_session

pytestmark = pytest.mark.filterwarnings(
    "ignore:Object of type <AccountEmail> not in session"
)


@pytest.fixture
def user(db_session: scoped_session) -> models.User:
    """User fixture."""
    new_user = models.User(
        username='user',
        fullname="User",
        password='test_password',  # noqa: S106
    )
    db_session.add(new_user)
    db_session.commit()
    return new_user


@pytest.fixture
def user_nameless(db_session: scoped_session) -> models.User:
    """User fixture without a username."""
    new_user = models.User(
        fullname="Nameless User",
        password='test_password_nameless',  # noqa: S106
    )
    db_session.add(new_user)
    new_user.add_email('nameless@example.com')
    db_session.commit()
    return new_user


@pytest.fixture
def user_named(db_session: scoped_session) -> models.User:
    """User fixture with a username."""
    new_user = models.User(
        username='user_named',
        fullname="Named User",
        password='test_password_named',  # noqa: S106
    )
    db_session.add(new_user)
    new_user.add_email('named@example.com')
    db_session.commit()
    return new_user


@pytest.fixture
def user_email(db_session: scoped_session, user: models.User) -> models.AccountEmail:
    """Email address for user fixture."""
    retval = user.add_email('user@example.com')
    db_session.commit()
    return retval


@pytest.fixture
def user_phone(db_session: scoped_session, user: models.User) -> models.AccountPhone:
    """Phone number for user fixture."""
    retval = user.add_phone('+912345678901')
    db_session.commit()
    return retval


def test_form_has_user(
    app: Flask, user: models.User, user_nameless: models.User, user_named: models.User
) -> None:
    """Login form identifies user correctly."""
    with app.test_request_context(method='POST', data={'username': 'user'}):
        form = forms.LoginForm(meta={'csrf': False})
        form.validate()
        assert form.user == user


def test_form_has_user_nameless(
    app: Flask, user: models.User, user_nameless: models.User, user_named: models.User
) -> None:
    """Login form identifies user correctly."""
    with app.test_request_context(
        method='POST', data={'username': 'nameless@example.com'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.LoginWithOtp):  # Since we did not provide a password
            form.validate()
        assert form.user == user_nameless


def test_form_has_user_named(
    app: Flask, user: models.User, user_nameless: models.User, user_named: models.User
) -> None:
    """Login form identifies user correctly."""
    with app.test_request_context(method='POST', data={'username': 'user_named'}):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.LoginWithOtp):  # Since we did not provide a password
            form.validate()
        assert form.user == user_named


def test_form_has_user_named_by_email(
    app: Flask, user: models.User, user_nameless: models.User, user_named: models.User
) -> None:
    """Login form identifies user correctly."""
    with app.test_request_context(
        method='POST', data={'username': 'named@example.com'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.LoginWithOtp):  # Since we did not provide a password
            form.validate()
        assert form.user == user_named


def test_login_no_data(app: Flask, user: models.User) -> None:
    """Login form fails if username and password are not provided."""
    with app.test_request_context(method='POST'):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == [form.username.validators[0].message]
        assert form.password.errors == []


def test_login_no_password(app: Flask, user: models.User) -> None:
    """Login fails if password is not provided and user has no email/phone."""
    with app.test_request_context(method='POST', data={'username': 'user'}):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == [form.password.validators[0].message]


def test_login_no_password_with_email(
    app: Flask, user: models.User, user_email: models.AccountEmail
) -> None:
    """Passwordless login if password is not provided but user has email."""
    with app.test_request_context(method='POST', data={'username': 'user'}):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.LoginWithOtp):
            assert form.validate() is True
        assert form.user == user
        assert form.anchor == user_email


def test_login_no_password_with_phone_and_email(
    app: Flask,
    user: models.User,
    user_email: models.AccountEmail,
    user_phone: models.AccountPhone,
) -> None:
    """Passwordless login if password is not provided but user has phone or email."""
    with app.test_request_context(method='POST', data={'username': 'user'}):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.LoginWithOtp):
            assert form.validate() is True
        assert form.user == user
        assert form.anchor == user_phone  # Phone number is default anchor


def test_login_no_password_with_email_and_phone(
    app: Flask,
    user: models.User,
    user_email: models.AccountEmail,
    user_phone: models.AccountPhone,
) -> None:
    """Passwordless login if password is not provided but user used email."""
    with app.test_request_context(method='POST', data={'username': 'user@example.com'}):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.LoginWithOtp):
            assert form.validate() is True
        assert form.user == user
        assert form.anchor == user_email  # The anchor used in username takes priority


def test_login_no_username(app: Flask, user: models.User) -> None:
    """Login fails if username is not provided."""
    with app.test_request_context(method='POST', data={'password': 'test_password'}):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == [form.username.validators[0].message]
        assert form.password.errors == []


def test_login_blank_username(app: Flask, user: models.User) -> None:
    """Login fails if username is blank."""
    with app.test_request_context(
        method='POST', data={'username': '', 'password': 'test_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == [form.username.validators[0].message]
        assert form.password.errors == []


def test_login_blank_password(app: Flask, user: models.User) -> None:
    """Login fails if password is blank."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': ''}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == [form.password.validators[0].message]


def test_login_wrong_username(app: Flask, user: models.User) -> None:
    """Login fails if username cannot identify a user."""
    with app.test_request_context(
        method='POST', data={'username': 'no_user', 'password': 'test_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == [forms.login.MSG_NO_ACCOUNT]
        assert form.password.errors == []


def test_login_wrong_password(app: Flask, user: models.User) -> None:
    """Login fails if password is incorrect."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'wrong_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == [forms.login.MSG_INCORRECT_PASSWORD]


def test_login_long_password(app: Flask, user: models.User) -> None:
    """Login fails if password candidate is too long."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'a' * 101}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == [
            form.password.validators[1].message % {'max': 100}
        ]


@pytest.mark.parametrize('username', ['unknown@example.com', '+919845012345'])
def test_login_no_probing(app: Flask, username: str) -> None:
    """Login fails if email/phone is not present, but as an incorrect password."""
    with app.test_request_context(
        method='POST', data={'username': username, 'password': 'wrong_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.username.errors == []
        assert form.password.errors == [forms.login.MSG_INCORRECT_PASSWORD]


def test_login_pass(app: Flask, user: models.User) -> None:
    """Login succeeds if both username and password match."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'test_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_email_pass(
    app: Flask, user: models.User, user_email: models.AccountEmail
) -> None:
    """Login succeeds if email and password match."""
    with app.test_request_context(
        method='POST', data={'username': str(user_email), 'password': 'test_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_phone_pass(
    app: Flask, user: models.User, user_phone: models.AccountPhone
) -> None:
    """Login succeeds if phone number and password match."""
    with app.test_request_context(
        method='POST', data={'username': str(user_phone), 'password': 'test_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_partial_phone_pass(
    app: Flask, user: models.User, user_phone: models.AccountPhone
) -> None:
    """Login succeeds if unprefixed phone number and password match."""
    with app.test_request_context(
        method='POST',
        data={'username': str(user_phone)[3:], 'password': 'test_password'},
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_user_suspended(app: Flask, user: models.User) -> None:
    """Login fails if the user account has been suspended."""
    user.mark_suspended()
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'test_password'}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        # FIXME: The user should be informed that their account has been suspended
        assert form.username.errors == [forms.login.MSG_NO_ACCOUNT]
        assert form.password.errors == []


def test_register_email_otp(app: Flask) -> None:
    """Login with non-existent account and valid email signals a registration."""
    with app.test_request_context(
        method='POST', data={'username': 'example@example.com', 'password': ''}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.RegisterWithOtp):
            form.validate()
        assert form.user is None
        assert form.anchor is None
        assert form.new_email == 'example@example.com'
        assert form.new_phone is None


@pytest.mark.parametrize(
    ('phone_number', 'full_phone_number'),
    [
        ('+919845012345', '+919845012345'),
        ('9845012345', '+919845012345'),
        ('+12345678900', '+12345678900'),
    ],
)
def test_register_phone_otp(
    app: Flask, phone_number: str, full_phone_number: str
) -> None:
    """Login with non-existent account and valid phone signals a registration."""
    with app.test_request_context(
        method='POST', data={'username': phone_number, 'password': ''}
    ):
        form = forms.LoginForm(meta={'csrf': False})
        with pytest.raises(forms.RegisterWithOtp):
            form.validate()
        assert form.user is None
        assert form.anchor is None
        assert form.new_email is None
        assert form.new_phone == full_phone_number
