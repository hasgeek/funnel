import unittest

from funnel import app

from .fixtures import Fixtures


class TestDatabaseFixture(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.fixtures = Fixtures()
        self.fixtures.make_fixtures()
        self.fixtures.test_client = app.test_client()
