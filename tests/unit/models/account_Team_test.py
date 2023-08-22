"""Tests for Team model."""

import pytest

from funnel import models

from .db_test import TestDatabaseFixture


class TestTeam(TestDatabaseFixture):
    def test_team_get(self) -> None:
        """Test for retrieving a Team with matching buid."""
        dachshunds = self.fixtures.dachshunds
        dachshunds_buid = dachshunds.buid
        result_with_buid = models.Team.get(buid=dachshunds_buid)
        assert isinstance(result_with_buid, models.Team)
        assert dachshunds.title == result_with_buid.title
        assert dachshunds.account == result_with_buid.account
        with pytest.raises(TypeError):
            models.Team.get()  # type: ignore[call-arg]  # pylint: disable=E1120

    def test_team_pickername(self) -> None:
        """Test for verifying team's pickername."""
        dachshunds = self.fixtures.dachshunds
        title = dachshunds.title
        pickername = dachshunds.pickername
        assert isinstance(pickername, str)
        assert title == pickername
