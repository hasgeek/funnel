"""Tests for the Update model."""

# pylint: disable=redefined-outer-name

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
def test_update_numbering_by_publish_order(
    request: pytest.FixtureRequest,
    db_session: scoped_session,
    user_vetinari: models.User,
    update1: str,
    update2: str,
    update3: str,
) -> None:
    """Updates are numbered by publish order."""
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


@pytest.mark.parametrize(
    ('update1', 'update2', 'update3'),
    permutations(['public_update', 'participant_update', 'member_update']),
)
def test_update_numbering_publish_after_delete(
    request: pytest.FixtureRequest,
    db_session: scoped_session,
    user_vetinari: models.User,
    update1: str,
    update2: str,
    update3: str,
) -> None:
    """Update numbers are incremental even if a previous update was deleted."""
    for number, fixture_name in enumerate([update1, update2, update3], 1):
        obj: models.Update = request.getfixturevalue(fixture_name)
        obj.publish(user_vetinari)
        db_session.commit()
        assert obj.number == number
        obj.delete(user_vetinari)
        db_session.commit()


def public_update_grants_reader_role_to_all(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_twoflower: models.User,
    public_update: models.Update,
) -> None:
    """A public update grants 'reader' role to all after it is published."""
    assert public_update.state.DRAFT
    assert not public_update.state.PUBLISHED
    # The project editor gets 'reader' role courtesy of being a crew member
    assert 'reader' in public_update.roles_for(user_vetinari)
    # Any other user does not as the update is still a draft
    assert 'reader' not in public_update.roles_for(user_twoflower)
    # Publishing the update changes these grants
    public_update.publish(user_vetinari)
    db_session.commit()
    assert not public_update.state.DRAFT
    assert public_update.state.PUBLISHED
    # Reader role is now granted to all users
    assert 'reader' in public_update.roles_for(user_vetinari)
    assert 'reader' in public_update.roles_for(user_twoflower)
    assert 'reader' in public_update.roles_for(None)
