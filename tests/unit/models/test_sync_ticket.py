import unittest

import pytest

from coaster.utils import uuid_b58
from funnel import app
from funnel.models import (
    EmailAddress,
    Organization,
    Project,
    SyncTicket,
    TicketClient,
    TicketEvent,
    TicketParticipant,
    TicketType,
    User,
)

from .event_models_fixtures import (
    event_ticket_types,
    ticket_list,
    ticket_list2,
    ticket_list3,
)


def bulk_upsert(project, ticket_event_list):
    for ticket_event_dict in ticket_event_list:
        ticket_event = TicketEvent.upsert(
            project,
            current_title=ticket_event_dict.get('title'),
            title=ticket_event_dict.get('title'),
            project=project,
        )
        for ticket_type_title in ticket_event_dict.get('ticket_types'):
            ticket_type = TicketType.upsert(
                project,
                current_name=None,
                current_title=ticket_type_title,
                project=project,
                title=ticket_type_title,
            )
            ticket_event.ticket_types.append(ticket_type)


@pytest.mark.usefixtures('db_session')
class TestEventModels(unittest.TestCase):
    app = app

    @pytest.fixture(autouse=True)
    def fixture_setup(self, request, db_session):
        self.db_session = db_session
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        # Initial Setup
        random_user_id = uuid_b58()
        self.user = User(
            username=f'lukes{random_user_id.lower()}',
            fullname="Luke Skywalker",
        )

        self.db_session.add(self.user)
        self.db_session.commit()

        self.organization = Organization(
            name='spacecon', title="SpaceCon", owner=self.user
        )
        self.db_session.add(self.organization)
        self.db_session.commit()
        self.profile = self.organization.profile

        self.project = Project(
            title="20000 AD",
            tagline="In a galaxy far far away...",
            profile=self.profile,
            user=self.user,
        )
        self.db_session.add(self.project)
        self.project.make_name()
        self.db_session.commit()

        self.ticket_client = TicketClient(
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
        def tearDown():
            self.ctx.pop()

    def test_import_from_list(self):
        # test bookings
        self.ticket_client.import_from_list(ticket_list)
        p1 = TicketParticipant.query.filter_by(
            email_address=EmailAddress.get('participant1@gmail.com'),
            project=self.project,
        ).one_or_none()
        p2 = TicketParticipant.query.filter_by(
            email_address=EmailAddress.get('participant2@gmail.com'),
            project=self.project,
        ).one_or_none()
        p3 = TicketParticipant.query.filter_by(
            email_address=EmailAddress.get('participant3@gmail.com'),
            project=self.project,
        ).one_or_none()
        assert SyncTicket.query.count() == 3
        assert TicketParticipant.query.count() == 3
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
        p4 = TicketParticipant.query.filter_by(
            email_address=EmailAddress.get('participant4@gmail.com'),
            project=self.project,
        ).one_or_none()
        assert len(p1.ticket_events) == 2
        assert len(p2.ticket_events) == 0
        assert len(p3.ticket_events) == 0
        assert len(p4.ticket_events) == 1
