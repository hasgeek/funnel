"""Feature test configuration."""
# pylint: disable=redefined-outer-name

import pytest


@pytest.fixture()
def db_session(db_session_truncate):
    """Use truncate mode for db session."""
    return db_session_truncate
