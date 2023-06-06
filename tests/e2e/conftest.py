"""Feature test configuration."""
# pylint: disable=redefined-outer-name

from pytest_socket import enable_socket
import pytest


@pytest.fixture()
def db_session(db_session_truncate):
    """Use truncate mode for db session."""
    return db_session_truncate


def pytest_runtest_setup() -> None:
    enable_socket()
