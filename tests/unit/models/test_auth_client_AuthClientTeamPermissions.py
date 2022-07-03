from funnel import models

from .test_db import TestDatabaseFixture


class TestTeamClientPermissions(TestDatabaseFixture):
    def test_teamclientpermissions(self):
        """Test for verifying creation of TeamClientPermissions' instance."""
        result = models.AuthClientTeamPermissions()
        assert isinstance(result, models.AuthClientTeamPermissions)

    def test_teamclientpermissions_pickername(self):
        """Test for retreiving pickername on TeamClientPermissions instance."""
        dachshunds = self.fixtures.dachshunds
        team_client_permission = self.fixtures.auth_client_team_permissions
        assert team_client_permission.pickername == dachshunds.title
