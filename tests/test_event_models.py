import unittest

from coaster.utils import buid
from funnel import app
from funnel.models import (
    Event,
    Participant,
    Profile,
    Project,
    SyncTicket,
    TicketClient,
    TicketType,
    User,
    db,
)

from .event_models_fixtures import (
    event_ticket_types,
    ticket_list,
    ticket_list2,
    ticket_list3,
)


def bulk_upsert(project, event_list):
    for event_dict in event_list:
        event = Event.upsert(
            project,
            current_title=event_dict.get('title'),
            title=event_dict.get('title'),
            project=project,
        )
        for ticket_type_title in event_dict.get('ticket_types'):
            ticket_type = TicketType.upsert(
                project,
                current_name=None,
                current_title=ticket_type_title,
                project=project,
                title=ticket_type_title,
            )
            event.ticket_types.append(ticket_type)


class TestEventModels(unittest.TestCase):
    app = app

    def setUp(self):
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        db.create_all()
        # Initial Setup
        random_user_id = buid()
        self.user = User(
            userid=random_user_id,
            username='lukes{userid}'.format(userid=random_user_id),
            fullname="Luke Skywalker",
            email='luke{userid}@dagobah.org'.format(userid=random_user_id),
        )

        db.session.add(self.user)
        db.session.commit()

        self.profile = Profile(title="SpaceCon", userid=self.user.userid)
        db.session.add(self.profile)
        db.session.commit()

        self.project = Project(
            title="20000 AD",
            tagline="In a galaxy far far away...",
            profile=self.profile,
            user=self.user,
        )
        self.project.make_name()
        db.session.add(self.project)
        db.session.commit()

        self.ticket_client = TicketClient(
            name="test client",
            client_eventid='123',
            clientid='123',
            client_secret='123',
            client_access_token='123',
            project=self.project,
        )
        db.session.add(self.ticket_client)
        db.session.commit()

        bulk_upsert(self.project, event_ticket_types)
        db.session.commit()

        self.session = db.session

    def tearDown(self):
        self.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_import_from_list(self):
        # test bookings
        self.ticket_client.import_from_list(ticket_list)
        p1 = Participant.query.filter_by(
            email='participant1@gmail.com', project=self.project
        ).one_or_none()
        p2 = Participant.query.filter_by(
            email='participant2@gmail.com', project=self.project
        ).one_or_none()
        p3 = Participant.query.filter_by(
            email='participant3@gmail.com', project=self.project
        ).one_or_none()
        self.assertEqual(SyncTicket.query.count(), 3)
        self.assertEqual(Participant.query.count(), 3)
        self.assertEqual(len(p1.events), 2)
        self.assertEqual(len(p2.events), 1)
        self.assertEqual(len(p3.events), 1)

        # test cancellations
        self.ticket_client.import_from_list(ticket_list2)
        self.assertEqual(len(p1.events), 2)
        self.assertEqual(len(p2.events), 0)
        self.assertEqual(len(p3.events), 1)

        # test_transfers
        self.ticket_client.import_from_list(ticket_list3)
        p4 = Participant.query.filter_by(
            email='participant4@gmail.com', project=self.project
        ).one_or_none()
        self.assertEqual(len(p1.events), 2)
        self.assertEqual(len(p2.events), 0)
        self.assertEqual(len(p3.events), 0)
        self.assertEqual(len(p4.events), 1)
