"""Feature test configuration."""

import pytest


@pytest.fixture()
def db_session(db_session_truncate):
    """Use truncate mode for db session."""
    return db_session_truncate


@pytest.fixture()
def firefox_en(firefox_options):
    firefox_options.set_preference('intl.accept_languages', 'en')
    return firefox_en


@pytest.fixture()
def firefox_hi(firefox_options):
    firefox_options.set_preference('intl.accept_languages', 'hi')
    return firefox_hi


@pytest.fixture()
def chrome_en(chrome_options):
    chrome_options.add_argument("--lang=en")
    return chrome_en


@pytest.fixture()
def chrome_hi(chrome_options):
    chrome_options.add_argument("--lang=hi")
    return chrome_en


@pytest.fixture()
def firefox_twoflower(firefox, login, user_twoflower):
    # Inject auth cookie of the user twoflower at login
    login._as(user_twoflower)
    # Generate lastuser cookie
    firefox.add_cookie({'last_user': '<cookie>'})
    return firefox_twoflower
