"""Tests for the Update model."""

from itertools import permutations

import pytest

from funnel import models

from ...conftest import scoped_session


@pytest.fixture()
def public_update(
    db_session: scoped_session,
    project_expo2010: models.Project,
    user_vetinari: models.User,
) -> models.Update:
    """Public update fixture."""
    update = models.Update(
        project=project_expo2010,
        created_by=user_vetinari,
        visibility='public',
        title="Public update",
        body="Public update body",
    )
    db_session.add(update)
    return update


@pytest.fixture()
def participant_update(
    db_session: scoped_session,
    project_expo2010: models.Project,
    user_vetinari: models.User,
) -> models.Update:
    """Participants-only update fixture."""
    update = models.Update(
        project=project_expo2010,
        created_by=user_vetinari,
        visibility='participants',
        title="Participant update",
        body="Participant update body",
    )
    db_session.add(update)
    return update


@pytest.fixture()
def member_update(
    db_session: scoped_session,
    project_expo2010: models.Project,
    user_vetinari: models.User,
) -> models.Update:
    """Members-only update fixture."""
    update = models.Update(
        project=project_expo2010,
        created_by=user_vetinari,
        visibility='members',
        title="Member update",
        body="Member update body",
    )
    db_session.add(update)
    return update


@pytest.mark.parametrize(
    ('update1', 'update2', 'update3'),
    permutations(['public_update', 'participant_update', 'member_update']),
)
def test_update_numbering(
    request: pytest.FixtureRequest,
    db_session: scoped_session,
    user_vetinari: models.User,
    update1: str,
    update2: str,
    update3: str,
) -> None:
    obj1: models.Update = request.getfixturevalue(update1)
    obj2: models.Update = request.getfixturevalue(update2)
    obj3: models.Update = request.getfixturevalue(update3)
    assert obj1.number is None
    assert obj2.number is None
    assert obj3.number is None
    obj1.publish(user_vetinari)
    obj2.publish(user_vetinari)
    obj3.publish(user_vetinari)
    db_session.commit()
    assert obj1.number == 1
    assert obj2.number == 2
    assert obj3.number == 3
