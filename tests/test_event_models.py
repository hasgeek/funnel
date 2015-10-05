# -*- coding: utf-8 -*-

import unittest
from flask import Flask
# from ..funnel.util import format_twitter, sync_from_list
from funnel import *
from funnel.models import (db, Profile, ProposalSpace, Event, User, SyncTicket, Participant, TicketClient)
from funnel.util import format_twitter

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:pg@localhost:5433/funnel_test'
db.init_app(app)


class TestEventModels(unittest.TestCase):
    app = app

    def setUp(self):
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        init_for('test')
        db.create_all()
        self.session = db.session

    def tearDown(self):
        self.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_event_models(self):
        ticket_list = [{
            'fullname': u'participant{id}'.format(id=unicode(1)),
            'email': u'participant{id}@gmail.com'.format(id=unicode(1)),
            'phone': u'123',
            'twitter': format_twitter(u'@p{id}'.format(id=unicode(1))),
            'job_title': u'Engineer',
            'company': u'Acme',
            'city': u'Atlantis',
            'ticket_no': u't{id}'.format(id=unicode(1)),
            'ticket_type': 'Combo',
            'order_no': u'o{id}'.format(id=unicode(1))
        },
        {
            'fullname': u'participant{id}'.format(id=unicode(2)),
            'email': u'participant{id}@gmail.com'.format(id=unicode(2)),
            'phone': u'123',
            'twitter': format_twitter(u'@p{id}'.format(id=unicode(2))),
            'job_title': u'Engineer',
            'company': u'Acme',
            'city': u'Atlantis',
            'ticket_no': u't{id}'.format(id=unicode(2)),
            'ticket_type': 'Workshop',
            'order_no': u'o{id}'.format(id=unicode(2))
        },
        {
            'fullname': u'participant{id}'.format(id=unicode(3)),
            'email': u'participant{id}@gmail.com'.format(id=unicode(3)),
            'phone': u'123',
            'twitter': format_twitter(u'@p{id}'.format(id=unicode(3))),
            'job_title': u'Engineer',
            'company': u'Acme',
            'city': u'Atlantis',
            'ticket_no': u't{id}'.format(id=unicode(3)),
            'ticket_type': 'Conference',
            'order_no': u'o{id}'.format(id=unicode(3))
        }
        ]

        user = User(userid=u"123", username=u"lukes", fullname=u"Luke Skywalker",
            email=u'luke@dagobah.org')

        db.session.add(user)
        db.session.commit()

        profile = Profile(title='SpaceCon', userid=u"123")
        db.session.add(profile)
        db.session.commit()
        space = ProposalSpace(title='2015', tagline='In a galaxy far far away...', profile=profile, user=user)
        db.session.add(space)
        db.session.commit()

        ticket_client = TicketClient(name="test client", client_eventid='123', clientid='123', client_secret='123', client_access_token='123', proposal_space=space)
        db.session.add(ticket_client)
        db.session.commit()

        event_ticket_types_mapping = [
            {'title': 'SpaceCon', 'ticket_types': ['Conference', 'Combo']},
            {'title': 'SpaceCon workshop', 'ticket_types': ['Workshop', 'Combo']},
        ]
        Event.sync_from_list(space, event_ticket_types_mapping)
        db.session.commit()

        ticket_client.import_from_list(space, ticket_list)
        self.assertEquals(SyncTicket.query.count(), 3)
        self.assertEquals(Participant.query.count(), 3)
        p1 = Participant.query.filter_by(email='participant1@gmail.com', proposal_space=space).one_or_none()
        p2 = Participant.query.filter_by(email='participant2@gmail.com', proposal_space=space).one_or_none()
        self.assertEquals(len(p1.events), 2)
        self.assertEquals(len(p2.events), 1)

        # test cancellations
        cancel_list = [SyncTicket.get(space, 'o2', 't2')]
        ticket_client.import_from_list(space, ticket_list, cancel_list=cancel_list)
        self.assertEquals(len(p2.events), 0)

        # test_transfers
        ticket_list2 = [{
            'fullname': u'participant{id}'.format(id=unicode(1)),
            'email': u'participant{id}@gmail.com'.format(id=unicode(1)),
            'phone': u'123',
            'twitter': format_twitter(u'@p{id}'.format(id=unicode(1))),
            'job_title': u'Engineer',
            'company': u'Acme',
            'city': u'Atlantis',
            'ticket_no': u't{id}'.format(id=unicode(1)),
            'ticket_type': 'Combo',
            'order_no': u'o{id}'.format(id=unicode(1))
        },
        {
            'fullname': u'participant{id}'.format(id=unicode(2)),
            'email': u'participant{id}@gmail.com'.format(id=unicode(2)),
            'phone': u'123',
            'twitter': format_twitter(u'@p{id}'.format(id=unicode(2))),
            'job_title': u'Engineer',
            'company': u'Acme',
            'city': u'Atlantis',
            'ticket_no': u't{id}'.format(id=unicode(3)),
            'ticket_type': 'Workshop',
            'order_no': u'o{id}'.format(id=unicode(3))
        }
        ]
        ticket_client.import_from_list(space, ticket_list2)
        self.assertEquals(len(p2.events), 1)
        self.assertEquals(p2.events[0], Event.get(space, 'spacecon'))
