"""Feature test configuration."""

# pylint: disable=redefined-outer-name

import pytest
from sqlalchemy.orm import scoped_session


@pytest.fixture()
def db_session(db_session_truncate: scoped_session) -> scoped_session:
    """Use truncate mode for db session."""
    return db_session_truncate


def pytest_collection_modifyitems(items):
    for item in items:
        if 'live_server' in getattr(item, 'fixturenames', ()):
            item.add_marker(pytest.mark.enable_socket())
