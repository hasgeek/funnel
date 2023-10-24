"""Test for project ticket sync models."""
# pylint: disable=attribute-defined-outside-init,redefined-outer-name

import pytest

from coaster.utils import uuid_b58

from funnel import models

# --- Fixture data

event_ticket_types = [
    {'title': 'SpaceCon', 'ticket_types': ['Conference', 'Combo']},
    {'title': 'SpaceCon workshop', 'ticket_types': ['Workshop', 'Combo']},
]

ticket_list = [
    {
        'fullname': f'participant{str(1)}',
        'email': f'participant{str(1)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(1)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(1)}',
        'ticket_type': 'Combo',
        'order_no': f'o{str(1)}',
        'status': 'confirmed',
    },
    {
        'fullname': f'participant{str(2)}',
        'email': f'participant{str(2)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(2)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(2)}',
        'ticket_type': 'Workshop',
        'order_no': f'o{str(2)}',
        'status': 'confirmed',
    },
    {
        'fullname': f'participant{str(3)}',
        'email': f'participant{str(3)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(3)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(3)}',
        'ticket_type': 'Conference',
        'order_no': f'o{str(3)}',
        'status': 'confirmed',
    },
]

ticket_list2 = [
    {
        'fullname': f'participant{str(1)}',
        'email': f'participant{str(1)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(1)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(1)}',
        'ticket_type': 'Combo',
        'order_no': f'o{str(1)}',
        'status': 'confirmed',
    },
    {
        'fullname': f'participant{str(2)}',
        'email': f'participant{str(2)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(2)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(2)}',
        'ticket_type': 'Workshop',
        'order_no': f'o{str(2)}',
        'status': 'cancelled',
    },
    {
        'fullname': f'participant{str(3)}',
        'email': f'participant{str(3)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(3)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(3)}',
        'ticket_type': 'Conference',
        'order_no': f'o{str(3)}',
        'status': 'confirmed',
    },
]

ticket_list3 = [
    {
        'fullname': f'participant{str(1)}',
        'email': f'participant{str(1)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(1)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(1)}',
        'ticket_type': 'Combo',
        'order_no': f'o{str(1)}',
        'status': 'confirmed',
    },
    {
        'fullname': f'participant{str(2)}',
        'email': f'participant{str(2)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(2)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(2)}',
        'ticket_type': 'Workshop',
        'order_no': f'o{str(2)}',
        'status': 'cancelled',
    },
    {
        'fullname': f'participant{str(4)}',
        'email': f'participant{str(4)}@gmail.com',
        'phone': '123',
        'twitter': f'p{str(4)}',
        'job_title': 'Engineer',
        'company': 'Acme',
        'city': 'Atlantis',
        'ticket_no': f't{str(3)}',
        'ticket_type': 'Conference',
        'order_no': f'o{str(3)}',
        'status': 'confirmed',
    },
]

# --- Tests and helpers


def bulk_upsert(project, ticket_event_list):
    for ticket_event_dict in ticket_event_list:
        ticket_event = models.TicketEvent.upsert(
            project,
            current_title=ticket_event_dict.get('title'),
            title=ticket_event_dict.get('title'),
            project=project,
        )
        for ticket_type_title in ticket_event_dict.get('ticket_types'):
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
    def _fixture_setup(self, request, db_session, app):
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

        self.ticket_client = models.TicketClient(  # nosec
            name="test client",
            client_eventid='123',
            clientid='123',
            client_secret='123',
            client_access_token='123',
            project=self.project,
        )
        self.db_session.add(self.ticket_client)
        self.db_session.commit()

        bulk_upsert(self.project, event_ticket_types)
        self.db_session.commit()

        self.session = self.db_session

        @request.addfinalizer
        def tearDown():  # skipcq: PTC-W0065
            self.ctx.pop()

    def test_import_from_list(self) -> None:
        # test bookings
        self.ticket_client.import_from_list(ticket_list)
        p1 = models.TicketParticipant.query.filter_by(
            email_address=models.EmailAddress.get('participant1@gmail.com'),
            project=self.project,
        ).one_or_none()
        p2 = models.TicketParticipant.query.filter_by(
            email_address=models.EmailAddress.get('participant2@gmail.com'),
            project=self.project,
        ).one_or_none()
        p3 = models.TicketParticipant.query.filter_by(
            email_address=models.EmailAddress.get('participant3@gmail.com'),
            project=self.project,
        ).one_or_none()
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
        ).one_or_none()
        assert len(p1.ticket_events) == 2
        assert len(p2.ticket_events) == 0
        assert len(p3.ticket_events) == 0
        assert len(p4.ticket_events) == 1
