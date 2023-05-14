"""Tests for Team member merger when merging user accounts."""
# pylint: disable=redefined-outer-name

from datetime import timedelta
from types import SimpleNamespace

import pytest
import sqlalchemy as sa

from funnel import models


@pytest.fixture()
def team_merge_data(db_session):
    user1 = models.User(
        username='user1',
        fullname="User 1",
        created_at=sa.func.utcnow() - timedelta(days=1),
    )
    user2 = models.User(username='user2', fullname="User 2")
    org = models.Organization(
        name='test_org_team_merge', title="Organization", owner=user1
    )
    team = models.Team(title="Team", organization=org)
    db_session.add_all([user1, user2, org, team])
    db_session.commit()

    return SimpleNamespace(**locals())


def test_team_migrate_user1(team_merge_data) -> None:
    """
    Test to verify teams are transferred when merging users.

    Scenario 1: First user is in a team
    """
    team_merge_data.team.users.append(team_merge_data.user1)
    team_merge_data.db_session.commit()
    assert list(team_merge_data.team.users) == [team_merge_data.user1]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []

    merged = models.merge_users(team_merge_data.user1, team_merge_data.user2)
    assert merged == team_merge_data.user1
    assert merged.teams == [team_merge_data.team]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []


def test_team_migrate_user2(team_merge_data) -> None:
    """
    Test to verify teams are transferred when merging users.

    Scenario 2: Second user is in a team
    """
    team_merge_data.team.users.append(team_merge_data.user2)
    team_merge_data.db_session.commit()
    assert list(team_merge_data.team.users) == [team_merge_data.user2]
    assert team_merge_data.user1.teams == []
    assert team_merge_data.user2.teams == [team_merge_data.team]

    merged = models.merge_users(team_merge_data.user1, team_merge_data.user2)
    assert merged == team_merge_data.user1
    assert merged.teams == [team_merge_data.team]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []


def test_team_migrate_user3(team_merge_data) -> None:
    """
    Test to verify teams are transferred when merging users.

    Scenario 3: Both users are in a team
    """
    team_merge_data.team.users.append(team_merge_data.user1)
    team_merge_data.team.users.append(team_merge_data.user2)
    team_merge_data.db_session.commit()
    assert set(team_merge_data.team.users) == {
        team_merge_data.user1,
        team_merge_data.user2,
    }
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == [team_merge_data.team]

    merged = models.merge_users(team_merge_data.user1, team_merge_data.user2)
    assert merged == team_merge_data.user1
    assert merged.teams == [team_merge_data.team]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []
