import pytest

from funnel import app
from funnel.forms import LoginForm
from funnel.models import User


@pytest.fixture
def user(db_session):
    user = User(username='user', fullname="User", password='test_password')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def user_nameless(db_session):
    user = User(fullname="Nameless User", password='test_password_nameless')
    db_session.add(user)
    user.add_email('nameless@example.com')
    db_session.commit()
    return user


@pytest.fixture
def user_named(db_session):
    user = User(
        username='user-named', fullname="Named User", password='test_password_named'
    )
    db_session.add(user)
    user.add_email('named@example.com')
    db_session.commit()
    return user


@pytest.fixture
def user_email(db_session, user):
    retval = user.add_email('user@example.com')
    db_session.commit()
    return retval


@pytest.fixture
def user_phone(db_session, user):
    retval = user.add_phone('+912345678901')
    db_session.commit()
    return retval


def test_form_has_user(user, user_nameless, user_named):
    """Login form identifies user correctly."""
    with app.test_request_context(method='POST', data={'username': 'user'}):
        form = LoginForm(meta={'csrf': False})
        form.validate()
        assert form.user == user


def test_form_has_user_nameless(user, user_nameless, user_named):
    """Login form identifies user correctly."""
    with app.test_request_context(
        method='POST', data={'username': 'nameless@example.com'}
    ):
        form = LoginForm(meta={'csrf': False})
        form.validate()
        assert form.user == user_nameless


def test_form_has_user_named(user, user_nameless, user_named):
    """Login form identifies user correctly."""
    with app.test_request_context(method='POST', data={'username': 'user-named'}):
        form = LoginForm(meta={'csrf': False})
        form.validate()
        assert form.user == user_named


def test_form_has_user_named_by_email(user, user_nameless, user_named):
    """Login form identifies user correctly."""
    with app.test_request_context(
        method='POST', data={'username': 'named@example.com'}
    ):
        form = LoginForm(meta={'csrf': False})
        form.validate()
        assert form.user == user_named


def test_login_no_data(user):
    """Login form fails if username and password are not provided."""
    with app.test_request_context(method='POST'):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == [form.username.validators[0].message]
        assert form.password.errors == [form.password.validators[0].message]


def test_login_no_password(user):
    """Login fails if password is not provided."""
    with app.test_request_context(method='POST', data={'username': 'user'}):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == [form.password.validators[0].message]


def test_login_no_username(user):
    """Login fails if username is not provided."""
    with app.test_request_context(method='POST', data={'password': 'test_password'}):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == [form.username.validators[0].message]
        assert form.password.errors == []


def test_login_blank_username(user):
    """Login fails if username is blank."""
    with app.test_request_context(
        method='POST', data={'username': '', 'password': 'test_password'}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == [form.username.validators[0].message]
        assert form.password.errors == []


def test_login_blank_password(user):
    """Login fails if password is blank."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': ''}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == [form.password.validators[0].message]


def test_login_wrong_username(user):
    """Login fails if username cannot identify a user."""
    with app.test_request_context(
        method='POST', data={'username': 'no_user', 'password': 'test_password'}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        assert form.username.errors == ["This user could not be identified"]
        assert form.password.errors == []


def test_login_wrong_password(user):
    """Login fails if password is incorrect."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'wrong_password'}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == ["Incorrect password"]


def test_login_long_password(user):
    """Login fails if password candidate is too long."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'a' * 101}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == ["Password must be under 100 characters"]


def test_login_pass(user):
    """Login succeeds if both username and password match."""
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'test_password'}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_email_pass(user, user_email):
    """Login succeeds if email and password match."""
    with app.test_request_context(
        method='POST', data={'username': str(user_email), 'password': 'test_password'}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_phone_pass(user, user_phone):
    """Login succeeds if phone number and password match."""
    with app.test_request_context(
        method='POST', data={'username': str(user_phone), 'password': 'test_password'}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_partial_phone_pass(user, user_phone):
    """Login succeeds if unprefixed phone number and password match."""
    with app.test_request_context(
        method='POST',
        data={'username': str(user_phone)[3:], 'password': 'test_password'},
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is True
        assert form.user == user
        assert form.username.errors == []
        assert form.password.errors == []


def test_login_user_suspended(user):
    """Login fails if the user account has been suspended."""
    user.mark_suspended()
    with app.test_request_context(
        method='POST', data={'username': 'user', 'password': 'test_password'}
    ):
        form = LoginForm(meta={'csrf': False})
        assert form.validate() is False
        assert form.user is None
        # FIXME: The user should be informed that their account has been suspended
        assert form.username.errors == ["This user could not be identified"]
        assert form.password.errors == []
