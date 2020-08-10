from datetime import timedelta
from types import SimpleNamespace

import pytest

from funnel import models


@pytest.fixture(scope='function')
def team_merge_data(test_client):
    db = models.db
    db.create_all()
    user1 = models.User(
        username='user1',
        fullname="User 1",
        created_at=db.func.utcnow() - timedelta(days=1),
    )
    user2 = models.User(username='user2', fullname="User 2")
    org = models.Organization(
        name='test-org-team-merge', title="Organization", owner=user1
    )
    team = models.Team(title="Team", organization=org)
    db.session.add_all([user1, user2, org, team])
    db.session.commit()

    yield SimpleNamespace(**locals())

    db.session.rollback()
    db.drop_all()


def test_team_migrate_user1(team_merge_data):
    """
    Test to verify teams are transferred when merging users.

    Scenario 1: First user is in a team
    """
    team_merge_data.team.users.append(team_merge_data.user1)
    team_merge_data.db.session.commit()
    assert list(team_merge_data.team.users) == [team_merge_data.user1]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []

    merged = models.merge_users(team_merge_data.user1, team_merge_data.user2)
    assert merged == team_merge_data.user1
    assert merged.teams == [team_merge_data.team]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []


def test_team_migrate_user2(team_merge_data):
    """
    Test to verify teams are transferred when merging users.

    Scenario 2: Second user is in a team
    """
    team_merge_data.team.users.append(team_merge_data.user2)
    team_merge_data.db.session.commit()
    assert list(team_merge_data.team.users) == [team_merge_data.user2]
    assert team_merge_data.user1.teams == []
    assert team_merge_data.user2.teams == [team_merge_data.team]

    merged = models.merge_users(team_merge_data.user1, team_merge_data.user2)
    assert merged == team_merge_data.user1
    assert merged.teams == [team_merge_data.team]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []


def test_team_migrate_user3(team_merge_data):
    """
    Test to verify teams are transferred when merging users.

    Scenario 3: Both users are in a team
    """
    team_merge_data.team.users.append(team_merge_data.user1)
    team_merge_data.team.users.append(team_merge_data.user2)
    team_merge_data.db.session.commit()
    assert list(team_merge_data.team.users) == [
        team_merge_data.user1,
        team_merge_data.user2,
    ]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == [team_merge_data.team]

    merged = models.merge_users(team_merge_data.user1, team_merge_data.user2)
    assert merged == team_merge_data.user1
    assert merged.teams == [team_merge_data.team]
    assert team_merge_data.user1.teams == [team_merge_data.team]
    assert team_merge_data.user2.teams == []
