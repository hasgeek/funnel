"""Tests for AuthClientTeamPermissions model."""

from funnel import models

from .db_test import TestDatabaseFixture


class TestTeamClientPermissions(TestDatabaseFixture):
    def test_teamclientpermissions(self) -> None:
        """Test for verifying creation of TeamClientPermissions' instance."""
        result = models.AuthClientTeamPermissions()
        assert isinstance(result, models.AuthClientTeamPermissions)

    def test_teamclientpermissions_pickername(self) -> None:
        """Test for retreiving pickername on TeamClientPermissions instance."""
        dachshunds = self.fixtures.dachshunds
        team_client_permission = self.fixtures.auth_client_team_permissions
        assert team_client_permission.pickername == dachshunds.title
