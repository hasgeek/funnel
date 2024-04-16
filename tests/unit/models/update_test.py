"""Tests for the Update model."""

# pylint: disable=redefined-outer-name

from itertools import permutations

import pytest

from funnel import models

from ...conftest import scoped_session

# MARK: Fixtures -----------------------------------------------------------------------


@pytest.fixture
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


@pytest.fixture
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


@pytest.fixture
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


@pytest.fixture
def vimes_admin(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    user_vetinari: models.User,
    user_vimes: models.User,
) -> models.AccountMembership:
    """Org admin membership for user Vimes."""
    membership = models.AccountMembership(
        account=org_ankhmorpork,
        member=user_vimes,
        is_owner=False,
        granted_by=user_vetinari,
    )
    db_session.add(membership)
    return membership


@pytest.fixture
def ridcully_editor(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    project_expo2010: models.Project,
) -> models.ProjectMembership:
    """Project editor membership for Ridcully."""
    membership = models.ProjectMembership(
        project=project_expo2010,
        member=user_ridcully,
        is_editor=True,
        is_promoter=False,
        is_usher=False,
        granted_by=user_vetinari,
    )
    db_session.add(membership)
    return membership


@pytest.fixture
def rincewind_participant(
    db_session: scoped_session,
    project_expo2010: models.Project,
    user_rincewind: models.User,
) -> models.Rsvp:
    rsvp = models.Rsvp(project=project_expo2010, participant=user_rincewind)
    db_session.add(rsvp)
    rsvp.rsvp_yes()
    return rsvp


# MARK: Tests --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('update1', 'update2', 'update3'),
    permutations(['public_update', 'participant_update', 'member_update']),
)
@pytest.mark.parametrize('delete', [True, False])
def test_update_numbering(
    request: pytest.FixtureRequest,
    db_session: scoped_session,
    user_vetinari: models.User,
    update1: str,
    update2: str,
    update3: str,
    delete: bool,
) -> None:
    """Update numbers are incremental even if a previous update was deleted."""
    for number, fixture_name in enumerate([update1, update2, update3], 1):
        obj: models.Update = request.getfixturevalue(fixture_name)
        obj.publish(user_vetinari)
        db_session.commit()
        assert obj.number == number
        if delete:
            obj.delete(user_vetinari)
            db_session.commit()


@pytest.mark.parametrize(
    'update_fixture', ['public_update', 'participant_update', 'member_update']
)
@pytest.mark.usefixtures('vimes_admin', 'ridcully_editor', 'rincewind_participant')
def test_draft_update_is_not_accessible(
    request: pytest.FixtureRequest,
    user_vetinari: models.User,
    user_ridcully: models.User,
    user_vimes: models.User,
    user_rincewind: models.User,
    user_twoflower: models.User,
    update_fixture: str,
) -> None:
    """A draft or deleted update is not accessible to anyone except project crew."""
    update: models.Update = request.getfixturevalue(update_fixture)
    assert update.state.DRAFT
    assert not update.state.PUBLISHED
    # The project editor gets 'reader' role courtesy of being a crew member
    assert 'reader' in update.roles_for(user_vetinari)
    assert 'reader' in update.roles_for(user_ridcully)
    # Any other user does not as the update is still a draft
    assert 'reader' not in update.roles_for(user_vimes)
    assert 'reader' not in update.roles_for(user_rincewind)
    assert 'reader' not in update.roles_for(user_twoflower)
    assert 'reader' not in update.roles_for(None)


@pytest.mark.usefixtures('vimes_admin', 'ridcully_editor', 'rincewind_participant')
def test_public_update_grants_reader_role_to_all(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_vimes: models.User,
    user_ridcully: models.User,
    user_rincewind: models.User,
    user_twoflower: models.User,
    public_update: models.Update,
) -> None:
    """A public update grants 'reader' role to all after it is published."""
    public_update.publish(user_vetinari)
    db_session.commit()
    assert public_update.state.PUBLISHED
    # Reader role is granted to all users (with or without specific roles; even anon)
    assert 'reader' in public_update.roles_for(user_twoflower)
    assert 'reader' in public_update.roles_for(user_vimes)
    assert 'reader' in public_update.roles_for(user_ridcully)
    assert 'reader' in public_update.roles_for(user_rincewind)
    assert 'reader' in public_update.roles_for(user_twoflower)
    assert 'reader' in public_update.roles_for(None)


@pytest.mark.usefixtures('vimes_admin', 'ridcully_editor', 'rincewind_participant')
def test_participant_update_grants_reader_role_to_participants(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    user_vimes: models.User,
    user_rincewind: models.User,
    user_twoflower: models.User,
    participant_update: models.Update,
) -> None:
    """A participant update grants 'reader' role to participants only."""
    participant_update.publish(user_vetinari)
    db_session.commit()
    # Reader role is granted to participants (and crew) but not anyone else
    assert 'reader' in participant_update.roles_for(user_vetinari)  # Crew
    assert 'reader' in participant_update.roles_for(user_ridcully)  # Crew
    assert 'reader' in participant_update.roles_for(user_rincewind)  # Participant
    assert 'reader' not in participant_update.roles_for(user_vimes)  # Admin/member
    assert 'reader' not in participant_update.roles_for(user_twoflower)  # Unrelated
    assert 'reader' not in participant_update.roles_for(None)  # Anonymous


@pytest.mark.usefixtures('vimes_admin', 'ridcully_editor', 'rincewind_participant')
def test_member_update_grants_reader_role_to_members_only(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_vimes: models.User,
    member_update: models.Update,
) -> None:
    """A member update grants 'reader' role to project members only."""
    member_update.publish(user_vetinari)
    db_session.commit()
    assert set(member_update.actors_with({'account_member'})) == {
        user_vetinari,
        user_vimes,
    }
