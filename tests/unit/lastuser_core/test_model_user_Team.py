import funnel.models as models

from .test_db import TestDatabaseFixture


class TestTeam(TestDatabaseFixture):
    def test_team_get(self):
        """
        Test for retrieving a Team with matching buid.
        """
        dachshunds = self.fixtures.dachshunds
        dachshunds_buid = dachshunds.buid
        result_with_buid = models.Team.get(buid=dachshunds_buid)
        assert dachshunds.title == result_with_buid.title
        assert dachshunds.organization == result_with_buid.organization
        with self.assertRaises(TypeError):
            models.Team.get()

    def test_team_pickername(self):
        """
        Test for verifying team's pickername
        """
        dachshunds = self.fixtures.dachshunds
        title = dachshunds.title
        pickername = dachshunds.pickername
        self.assertIsInstance(pickername, str)
        self.assertEqual(title, pickername)

    def test_team_permissions(self):
        """
        Test for retrieving permissions for owner of a team
        """
        crusoe = self.fixtures.crusoe
        dachshunds = self.fixtures.dachshunds
        permissions_expected = ['edit', 'delete']
        result = dachshunds.permissions(crusoe)
        self.assertIsInstance(result, set)
        permissions_received = []
        for each in result:
            permissions_received.append(each)
        self.assertCountEqual(permissions_expected, permissions_received)

    def test_team_migrate_user(self):
        """
        Test for migrating an old user to newuser in a team (when merging user account takes place)
        """
