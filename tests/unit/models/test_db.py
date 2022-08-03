"""Fixture class for legacy tests."""
# pylint: disable=attribute-defined-outside-init

import unittest

import pytest

from .fixtures import Fixtures


class TestDatabaseFixture(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _pytest_fixtures(self, app, client, db_session):
        self.client = client
        self.db_session = db_session
        self.app = app
        self.fixtures = Fixtures()
        self.fixtures.make_fixtures(db_session)
