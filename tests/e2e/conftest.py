"""Feature test configuration."""

# pylint: disable=redefined-outer-name

import pytest
from playwright.sync_api import expect
from pytest_socket import enable_socket
from sqlalchemy.orm import scoped_session

expect.set_options(timeout=10_000)


@pytest.fixture
def db_session(db_session_truncate: scoped_session) -> scoped_session:
    """Use truncate mode for db session."""
    return db_session_truncate


def pytest_runtest_setup() -> None:
    enable_socket()
