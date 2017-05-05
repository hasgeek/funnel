# -*- coding: utf-8 -*-

import random
import unittest
from funnel import *
from funnel.models import (db, Profile, ProposalSpace, Event, User, SyncTicket, Participant, TicketClient, TicketType)
from .event_models_fixtures import event_ticket_types, ticket_list, ticket_list2, ticket_list3


def bulk_upsert(space, event_list):
    for event_dict in event_list:
        event = Event.upsert(space, current_title=event_dict.get('title'), title=event_dict.get('title'), proposal_space=space)
        for ticket_type_title in event_dict.get('ticket_types'):
            ticket_type = TicketType.upsert(space, current_name=None, current_title=ticket_type_title, proposal_space=space, title=ticket_type_title)
            event.ticket_types.append(ticket_type)


class TestEventModels(unittest.TestCase):
    app = app

    def setUp(self):
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        db.create_all()
        # Initial Setup
        random_user_id = random.randint(1, 1000)
        self.user = User(userid=unicode(random_user_id), username=u'lukes{userid}'.format(userid=random_user_id), fullname=u"Luke Skywalker",
            email=u'luke{userid}@dagobah.org'.format(userid=random_user_id))

        db.session.add(self.user)
        db.session.commit()

        self.profile = Profile(title='SpaceCon', userid=self.user.userid)
        db.session.add(self.profile)
        db.session.commit()

        self.space = ProposalSpace(title='20000 AD', tagline='In a galaxy far far away...', profile=self.profile, user=self.user)
        db.session.add(self.space)
        db.session.commit()

        self.ticket_client = TicketClient(name="test client", client_eventid='123', clientid='123', client_secret='123', client_access_token='123', proposal_space=self.space)
        db.session.add(self.ticket_client)
        db.session.commit()

        bulk_upsert(self.space, event_ticket_types)
        db.session.commit()

        self.session = db.session

    def tearDown(self):
        self.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_import_from_list(self):
        # test bookings
        self.ticket_client.import_from_list(ticket_list)
        p1 = Participant.query.filter_by(email='participant1@gmail.com', proposal_space=self.space).one_or_none()
        p2 = Participant.query.filter_by(email='participant2@gmail.com', proposal_space=self.space).one_or_none()
        p3 = Participant.query.filter_by(email='participant3@gmail.com', proposal_space=self.space).one_or_none()
        self.assertEquals(SyncTicket.query.count(), 3)
        self.assertEquals(Participant.query.count(), 3)
        self.assertEquals(len(p1.events), 2)
        self.assertEquals(len(p2.events), 1)
        self.assertEquals(len(p3.events), 1)

        # test cancellations
        self.ticket_client.import_from_list(ticket_list2)
        self.assertEquals(len(p1.events), 2)
        self.assertEquals(len(p2.events), 0)
        self.assertEquals(len(p3.events), 1)

        # test_transfers
        self.ticket_client.import_from_list(ticket_list3)
        p4 = Participant.query.filter_by(email='participant4@gmail.com', proposal_space=self.space).one_or_none()
        self.assertEquals(len(p1.events), 2)
        self.assertEquals(len(p2.events), 0)
        self.assertEquals(len(p3.events), 0)
        self.assertEquals(len(p4.events), 1)
