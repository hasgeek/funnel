"""Tests for fixtures in conftest."""

import pytest


def test_getuser_fixture(models, getuser) -> None:
    """Test the getuser fixture."""
    for username in getuser.usermap:
        user = getuser(username)
        assert isinstance(user, models.User)
        assert username in user.title


@pytest.mark.mock_config('app', {'TESTING': False})
@pytest.mark.mock_config('shortlinkapp', {'TESTING': lambda: ...})
def test_mock_config_set_testing_flag(app, shortlinkapp) -> None:
    """Mock config is correctly applied (set or remove, callable or direct value)."""
    assert 'TESTING' in app.config
    assert not app.config['TESTING']
    assert 'TESTING' not in shortlinkapp.config


def test_mock_config_removed(app, shortlinkapp) -> None:
    """Original config is restored after a mock config test (must run after above)."""
    assert 'TESTING' in app.config
    assert 'TESTING' in shortlinkapp.config
    assert app.config['TESTING']
    assert shortlinkapp.config['TESTING']
    assert shortlinkapp.config['TESTING']
