#!/usr/bin/env python

from flask import *
from funnel import init_for
from funnel.models import (db, Profile, ProposalSpace, Event, TicketType, Participant, SyncTicket, Attendee)
import csv
from urlparse import urlparse
import sys

init_for('dev')


def format_twitter(twitter_id):
    """formats a user given twitter handle
       Eg: https://twitter.com/shreyas_satish -> shreyas_satish, @shreyas_satish -> shreyas_satish
    """
    return urlparse(str(twitter_id)).path.replace('/', '').replace('@', '')


class ExplaraTicket(object):
    # model of an explara ticket obtained from their CSV
    def __init__(self, row):
        self.row = row

    def participant_from_ticket(self, space_id):
        return Participant(
            fullname=self.get('fullname'),
            email=self.get('email'),
            phone=self.get('phone'),
            twitter=format_twitter(self.get('twitter')),
            job_title=self.get('job_title'),
            company=self.get('company'),
            city=self.get('city'),
            proposal_space_id=space_id
        )

    def get(self, attr):
        """ returns the value of the requested attributed by
            referring to a map of attributes and their respective column
            indexes in the CSV
        """
        attrs = {
            'fullname': 1,
            'email': 2,
            'ticket_type': 3,
            'order_no': 5,
            'ticket_no': 6,
            'phone': 9,
            'job_title': 12,
            'company': 13,
            'city': 14,
            'twitter': 15
        }
        return str(self.row[attrs[attr]]).strip()


def sync_ticket_types(ticket_types, space_id):
    for name in ticket_types:
        ticket_type = TicketType.query.filter_by(name=name, proposal_space_id=space_id).first()
        if not ticket_type:
            ticket_type = TicketType(name=name, proposal_space_id=space_id)
            db.session.add(ticket_type)
    db.session.commit()


def sync_events(events, space_id):
    for e in events:
        event = Event.query.filter_by(name=e['name'], proposal_space_id=space_id).first()
        if not event:
            event = Event(name=e['name'], proposal_space_id=space_id)
            db.session.add(event)
            db.session.commit()
        for tt in e['ticket_types']:
            if tt not in [ticket_type.name for ticket_type in event.ticket_types]:
                event.ticket_types.append(TicketType.query.filter_by(name=tt).first())
    db.session.commit()


def get_rows_from_csv(csv_file, skip_header=True):
    with open(csv_file, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        if skip_header:
            next(reader)
        return [row for row in reader]


def sync_tickets(space, csv_file):
    tickets = get_rows_from_csv(csv_file)

    for item in tickets:
        et = ExplaraTicket(item)
        ticket = SyncTicket.query.filter_by(ticket_no=et.get('ticket_no')).first()

        ticket_ticket_type = TicketType.query.filter_by(name=et.get('ticket_type'), proposal_space_id=space.id).first()

        # get or create participant
        ticket_participant = Participant.query.filter_by(email=et.get('email')).first()
        if not ticket_participant:
            # create a new participant record if required
            ticket_participant = et.participant_from_ticket(space.id)
            db.session.add(ticket_participant)
            db.session.commit()

        if ticket:
            # check if participant has changed
            if ticket.participant is not ticket_participant:
                # update the participant record attached to the ticket
                ticket.participant = ticket_participant
        else:
            ticket = SyncTicket(
                ticket_no=et.get('ticket_no'),
                order_no=et.get('order_no'),
                ticket_type=ticket_ticket_type,
                participant=ticket_participant
            )
            db.session.add(ticket)
            db.session.commit()
            # for event in space.events:
        for event in ticket.ticket_type.events:
            a = Attendee.query.filter_by(event_id=event.id, participant_id=ticket.participant.id).first()
            if not a:
                a = Attendee(event_id=event.id, participant_id=ticket.participant.id)
            db.session.add(a)
            db.session.commit()


def sync_metarefresh(profile_name, space_name, ticket_types, events, csv_file):
    print "Syncing {0} - {1}".format(profile_name, space_name)
    profile = Profile.query.filter_by(name=profile_name).first()
    space = ProposalSpace.query.filter_by(name=space_name).filter_by(profile_id=profile.id).first()
    sync_ticket_types(ticket_types, space.id)
    sync_events(events, space.id)
    sync_tickets(space, csv_file)
    print "Done"

if __name__ == '__main__':
    if sys.argv[1] == 'metarefresh':
        mr_ticket_types = ["ReactJS Workshop", "Performance audit workshop", "Offline registrations for ReactJS workshop", "Offline registrations for Performance Audit workshop", "T-shirt", "Super early geek", "Early geek", "Regular", "Late", "Offline registrations and payment", "Single day pass - 16th April", "Single day pass - 17th April"]
        mr_events = [
            {'name': 'MetaRefresh Day 1', 'ticket_types': ["Super early geek", "Early geek", "Regular", "Late", "Offline registrations and payment", "Single day pass - 16th April"]},
            {'name': 'MetaRefresh Day 2', 'ticket_types': ["Super early geek", "Early geek", "Regular", "Late", "Offline registrations and payment", "Single day pass - 17th April"]},
            {'name': 'ReactJS Workshop', 'ticket_types': ["ReactJS Workshop", "Offline registrations for ReactJS workshop"]},
            {'name': 'Performance Audit Workshop', 'ticket_types': ["Performance audit workshop", "Offline registrations for Performance Audit workshop"]},
        ]
        sync_metarefresh(sys.argv[1], sys.argv[2], mr_ticket_types, mr_events, sys.argv[3])
