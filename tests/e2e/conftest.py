"""Feature test configuration."""
# pylint: disable=redefined-outer-name

import pytest


@pytest.fixture()
def db_session(db_session_truncate):
    """Use truncate mode for db session."""
    return db_session_truncate


def pytest_collection_modifyitems(items):
    for item in items:
        if 'live_server' in getattr(item, 'fixturenames', ()):
            item.add_marker(pytest.mark.enable_socket())
