"""Tests for fixtures in conftest."""


def test_getuser_fixture(models, getuser) -> None:
    """Test the getuser fixture."""
    for username in getuser.usermap:
        user = getuser(username)
        assert isinstance(user, models.User)
        assert username in user.title
