"""Test for project ticket sync models."""

# pylint: disable=attribute-defined-outside-init,redefined-outer-name

from typing import TypedDict

import pytest

from coaster.utils import uuid_b58

from funnel import models
from funnel.extapi.typing import ExtTicketsDict

from ...conftest import Flask, scoped_session

# MARK: Fixture data


class TicketEventTypeDict(TypedDict):
    title: str
    ticket_types: list[str]


event_ticket_types: list[TicketEventTypeDict] = [
    {'title': 'SpaceCon', 'ticket_types': ['Conference', 'Combo']},
    {'title': 'SpaceCon workshop', 'ticket_types': ['Workshop', 'Combo']},
]

ticket_list: list[ExtTicketsDict] = [
    {
        'fullname': 'participant1',
        'email': 'participant1@gmail.com',
        'phone': '123',
        'twitter': 'p1',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't1',
        'ticket_type': 'Combo',
        'order_no': 'o1',
        'status': 'confirmed',
    },
    {
        'fullname': 'participant2',
        'email': 'participant2@gmail.com',
        'phone': '123',
        'twitter': 'p2',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't2',
        'ticket_type': 'Workshop',
        'order_no': 'o2',
        'status': 'confirmed',
    },
    {
        'fullname': 'participant3',
        'email': 'participant3@gmail.com',
        'phone': '123',
        'twitter': 'p3',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't3',
        'ticket_type': 'Conference',
        'order_no': 'o3',
        'status': 'confirmed',
    },
]

ticket_list2: list[ExtTicketsDict] = [
    {
        'fullname': 'participant1',
        'email': 'participant1@gmail.com',
        'phone': '123',
        'twitter': 'p1',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't1',
        'ticket_type': 'Combo',
        'order_no': 'o1',
        'status': 'confirmed',
    },
    {
        'fullname': 'participant2',
        'email': 'participant2@gmail.com',
        'phone': '123',
        'twitter': 'p2',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't2',
        'ticket_type': 'Workshop',
        'order_no': 'o2',
        'status': 'cancelled',
    },
    {
        'fullname': 'participant3',
        'email': 'participant3@gmail.com',
        'phone': '123',
        'twitter': 'p3',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't3',
        'ticket_type': 'Conference',
        'order_no': 'o3',
        'status': 'confirmed',
    },
]

ticket_list3: list[ExtTicketsDict] = [
    {
        'fullname': 'participant1',
        'email': 'participant1@gmail.com',
        'phone': '123',
        'twitter': 'p1',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't1',
        'ticket_type': 'Combo',
        'order_no': 'o1',
        'status': 'confirmed',
    },
    {
        'fullname': 'participant2',
        'email': 'participant2@gmail.com',
        'phone': '123',
        'twitter': 'p2',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't2',
        'ticket_type': 'Workshop',
        'order_no': 'o2',
        'status': 'cancelled',
    },
    {
        'fullname': f'participant{4!s}',
        'email': f'participant{4!s}@gmail.com',
        'phone': '123',
        'twitter': f'p{4!s}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': 't3',
        'ticket_type': 'Conference',
        'order_no': 'o3',
        'status': 'confirmed',
    },
]

# MARK: Tests and helpers


def bulk_upsert(
    project: models.Project, ticket_event_list: list[TicketEventTypeDict]
) -> None:
    for ticket_event_dict in ticket_event_list:
        ticket_event = models.TicketEvent.upsert(
            project,
            current_title=ticket_event_dict['title'],
            title=ticket_event_dict['title'],
            project=project,
        )
        for ticket_type_title in ticket_event_dict['ticket_types']:
            ticket_type = models.TicketType.upsert(
                project,
                current_name=None,
                current_title=ticket_type_title,
                project=project,
                title=ticket_type_title,
            )
            ticket_event.ticket_types.append(ticket_type)


@pytest.mark.usefixtures('db_session')
class TestEventModels:
    @pytest.fixture(autouse=True)
    def _fixture_setup(
        self,
        request: pytest.FixtureRequest,
        db_session: scoped_session,
        app: Flask,
    ) -> None:
        self.db_session = db_session
        self.ctx = app.test_request_context()
        self.ctx.push()
        # Initial Setup
        random_user_id = uuid_b58()
        self.user = models.User(
            username=f'lukes{random_user_id.lower()}',
            fullname="Luke Skywalker",
        )

        self.db_session.add(self.user)
        self.db_session.commit()

        self.organization = models.Organization(
            name='spacecon', title="SpaceCon", owner=self.user
        )
        self.db_session.add(self.organization)
        self.db_session.commit()

        self.project = models.Project(
            title="20000 AD",
            tagline="In a galaxy far far away...",
            account=self.organization,
            created_by=self.user,
        )
        self.db_session.add(self.project)
        self.project.make_name()
        self.db_session.commit()

        self.ticket_client = models.TicketClient(
            name="test client",
            client_eventid='123',
            clientid='123',
            client_secret='123',  # noqa: S106
            client_access_token='123',  # noqa: S106
            project=self.project,
        )
        self.db_session.add(self.ticket_client)
        self.db_session.commit()

        bulk_upsert(self.project, event_ticket_types)
        self.db_session.commit()

        self.session = self.db_session

        @request.addfinalizer
        def tearDown() -> None:  # skipcq: PTC-W0065
            self.ctx.pop()

    def test_import_from_list(self) -> None:
        # test bookings
        self.ticket_client.import_from_list(ticket_list)
        p1 = models.TicketParticipant.query.filter_by(
            email_address=models.EmailAddress.get('participant1@gmail.com'),
            project=self.project,
        ).one()
        p2 = models.TicketParticipant.query.filter_by(
            email_address=models.EmailAddress.get('participant2@gmail.com'),
            project=self.project,
        ).one()
        p3 = models.TicketParticipant.query.filter_by(
            email_address=models.EmailAddress.get('participant3@gmail.com'),
            project=self.project,
        ).one()
        assert models.SyncTicket.query.count() == 3
        assert models.TicketParticipant.query.count() == 3
        assert len(p1.ticket_events) == 2
        assert len(p2.ticket_events) == 1
        assert len(p3.ticket_events) == 1

        # test cancellations
        self.ticket_client.import_from_list(ticket_list2)
        assert len(p1.ticket_events) == 2
        assert len(p2.ticket_events) == 0
        assert len(p3.ticket_events) == 1

        # test_transfers
        self.ticket_client.import_from_list(ticket_list3)
        p4 = models.TicketParticipant.query.filter_by(
            email_address=models.EmailAddress.get('participant4@gmail.com'),
            project=self.project,
        ).one()
        assert len(p1.ticket_events) == 2
        assert len(p2.ticket_events) == 0
        assert len(p3.ticket_events) == 0
        assert len(p4.ticket_events) == 1


# MARK: Participant role and access control tests

# To test role assignment, we assign different participants to different events across
# four projects. Stories:

# 1. Great God Om presides over the city expos but isn't so honoured at the workshops
# 2. Death is omnipresent
# 3. Twoflower as a tourist signs up for Expo 2010, for both days, and the workshop too,
#    but doesn't return in 2011
# 4. Rincewind meets Twoflower and joins for day 2 of Expo 2010 and the workshop, also
#    not returning in 2011
# 5. Ridcully gets honorary tickets for opening day of both city events, and for the
#    workshops at his university, whether he shows up or not
# 6. Ponder Stibbons doesn't care for the expo but is at the workshops both times
# 7. Vimes was not in charge until 2011, and isn't interested in the workshops
# 8. Dibbler is enthusiastically hawking at the expo but isn't allowed at the
#    workshops

# Table for visual reference against the Python structure:
# # | User      | Expo 2010 | Expo 2011 | AI 1     | AI 2
# --+----------+-----------+-----------+----------+------
# 1 | Om        | Day1/Day2 | Day1/Day2 |          |
# 2 | Death     | Day1/Day2 | Day1/Day2 | Workshop | Workshop
# 3 | Twoflower | Day1/Day2 |           | Workshop |
# 4 | Rincewind |      Day2 |           | Workshop |
# 5 | Ridcully  | Day1      | Day1      | Workshop | Workshop
# 6 | Stibbons  |           |           | Workshop | Workshop
# 7 | Vimes     |           | Day1/Day2 |          |
# 8 | Dibbler   | Day1/Day2 | Day1/Day2 |          |
participant_assignments: list[tuple[str, list[list[str] | None]]] = [
    ('user_om', [['day1', 'day2'], ['day1', 'day2'], None, None]),
    ('user_death', [['day1', 'day2'], ['day1', 'day2'], ['workshop'], ['workshop']]),
    ('user_twoflower', [['day1', 'day2'], None, ['workshop'], None]),
    ('user_rincewind', [['day2'], None, ['workshop'], None]),
    ('user_ridcully', [['day1'], ['day1'], ['workshop'], ['workshop']]),
    ('user_ponder_stibbons', [None, None, ['workshop'], ['workshop']]),
    ('user_vimes', [None, ['day1', 'day2'], None, None]),
    ('user_dibbler', [['day1', 'day2'], ['day1', 'day2'], None, None]),
]


@pytest.fixture
def ticket_events(
    db_session: scoped_session,
    project_expo2010: models.Project,
    project_expo2011: models.Project,
    project_ai1: models.Project,
    project_ai2: models.Project,
) -> dict[str, models.TicketEvent]:
    """Create ticket events for the project."""
    db_session.flush()
    events: dict[str, models.TicketEvent] = {}
    for project in (project_expo2010, project_expo2011):
        events[f'{project.name}-day1'] = models.TicketEvent(
            project=project,
            title="Day 1",
        )
        events[f'{project.name}-day2'] = models.TicketEvent(
            project=project,
            title="Day 2",
        )
    for project in (project_ai1, project_ai2):
        events[f'{project.name}-workshop'] = models.TicketEvent(
            project=project,
            title="Workshop",
        )
    db_session.add_all(events.values())
    return events


@pytest.fixture
def ticket_participants(
    request: pytest.FixtureRequest,
    db_session: scoped_session,
    project_expo2010: models.Project,
    project_expo2011: models.Project,
    project_ai1: models.Project,
    project_ai2: models.Project,
    ticket_events: dict[str, models.TicketEvent],
) -> list[models.TicketParticipant]:
    """Create ticket participants for the project."""
    db_session.flush()
    participants: list[models.TicketParticipant] = []
    for user_fixture, event_assignments in participant_assignments:
        user = request.getfixturevalue(user_fixture)
        assert isinstance(user, models.User)
        for project, event_names in zip(
            [project_expo2010, project_expo2011, project_ai1, project_ai2],
            event_assignments,
            strict=True,
        ):
            if event_names is not None:
                participants.append(
                    models.TicketParticipant(
                        project=project,
                        participant=user,
                        email=f'{user.username or user.fullname.lower()}@example.com',
                        fullname=user.fullname,
                        ticket_events=[
                            ticket_events[f'{project.name}-{event_name}']
                            for event_name in event_names
                        ],
                    )
                )
    db_session.add_all(participants)
    db_session.commit()
    return participants


def test_ticket_participant_rolecheck_no_dupes(
    project_expo2010: models.Project,
    project_expo2011: models.Project,
    project_ai1: models.Project,
    project_ai2: models.Project,
    ticket_participants: list[models.TicketParticipant],
) -> None:
    """Test that participants aren't repeated if they're in multiple events."""
    for project in (project_expo2010, project_expo2011, project_ai1, project_ai2):
        assert len(list(project.has_ticket_participant_role)) == len(
            set(project.has_ticket_participant_role)
        )


# Expected role presence:
# User      | Expo 2010 | Expo 2011 | AI 1  | AI 2
# ----------+-----------+-----------+-------+------
# Om        | True      | True      | False | False
# Death     | True      | True      | True  | True
# Twoflower | True      | False     | True  | False
# Rincewind | True      | False     | True  | False
# Ridcully  | True      | True      | True  | True
# Stibbons  | False     | False     | True  | True
# Vimes     | False     | True      | False | False
# Dibbler   | True      | True      | False | False


def test_ticket_participant_rolecheck_count(
    project_expo2010: models.Project,
    project_expo2011: models.Project,
    project_ai1: models.Project,
    project_ai2: models.Project,
    ticket_participants: list[models.TicketParticipant],
) -> None:
    """Test that the count of participants matches expectation (hardcoded here)."""
    assert len(list(project_expo2010.has_ticket_participant_role)) == 6
    assert len(list(project_expo2011.has_ticket_participant_role)) == 5
    assert len(list(project_ai1.has_ticket_participant_role)) == 5
    assert len(list(project_ai2.has_ticket_participant_role)) == 3


def test_ticket_participant_role_count(
    project_expo2010: models.Project,
    project_expo2011: models.Project,
    project_ai1: models.Project,
    project_ai2: models.Project,
    ticket_participants: list[models.TicketParticipant],
) -> None:
    """Test that the count of participants matches expectation (hardcoded here)."""
    assert len(list(project_expo2010.actors_with({'ticket_participant'}))) == 6
    assert len(list(project_expo2011.actors_with({'ticket_participant'}))) == 5
    assert len(list(project_ai1.actors_with({'ticket_participant'}))) == 5
    assert len(list(project_ai2.actors_with({'ticket_participant'}))) == 3


@pytest.mark.parametrize(
    ('user_fixture', 'event_assignments'),
    participant_assignments,
)
def test_ticket_participant_role_access(
    request: pytest.FixtureRequest,
    user_fixture: str,
    event_assignments: list[list[str] | None],
    project_expo2010: models.Project,
    project_expo2011: models.Project,
    project_ai1: models.Project,
    project_ai2: models.Project,
    ticket_participants: list[models.TicketParticipant],
) -> None:
    """Test user is or isn't a participant in each project."""
    user = request.getfixturevalue(user_fixture)
    assert isinstance(user, models.User)
    for project, event_names in zip(
        [project_expo2010, project_expo2011, project_ai1, project_ai2],
        event_assignments,
        strict=True,
    ):
        if event_names is None:
            assert 'ticket_participant' not in project.roles_for(user)
        else:
            assert 'ticket_participant' in project.roles_for(user)
            for ticket_participant in project.ticket_participants:
                if ticket_participant.participant == user:
                    assert len(ticket_participant.ticket_events) == len(event_names)
                    break
            else:
                pytest.fail(f"User {user.fullname} not found in project {project.name}")


def test_ticket_participant_role_list(
    user_om: models.User,
    user_death: models.User,
    user_twoflower: models.User,
    user_rincewind: models.User,
    user_ridcully: models.User,
    user_ponder_stibbons: models.User,
    user_vimes: models.User,
    user_dibbler: models.User,
    project_expo2010: models.Project,
    project_expo2011: models.Project,
    project_ai1: models.Project,
    project_ai2: models.Project,
    ticket_participants: list[models.TicketParticipant],
) -> None:
    """Test that the list of participants matches expectation (hardcoded here)."""
    assert set(project_expo2010.actors_with({'ticket_participant'})) == {
        user_death,
        user_dibbler,
        user_om,
        user_ridcully,
        user_rincewind,
        user_twoflower,
    }
    assert set(project_expo2011.actors_with({'ticket_participant'})) == {
        user_death,
        user_dibbler,
        user_om,
        user_ridcully,
        user_vimes,
    }
    assert set(project_ai1.actors_with({'ticket_participant'})) == {
        user_death,
        user_ponder_stibbons,
        user_ridcully,
        user_rincewind,
        user_twoflower,
    }
    assert set(project_ai2.actors_with({'ticket_participant'})) == {
        user_death,
        user_ponder_stibbons,
        user_ridcully,
    }
