"""Fixture class for legacy tests."""
# pylint: disable=attribute-defined-outside-init

import pytest

from .fixtures import Fixtures


class TestDatabaseFixture:
    @pytest.fixture(autouse=True)
    def _pytest_fixtures(self, models, app, client, db_session):
        self.client = client
        self.db_session = db_session
        self.app = app
        self.fixtures = Fixtures()
        self.fixtures.make_fixtures(models, db_session)
