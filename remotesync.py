#!/usr/bin/env python

from flask import *
from funnel import init_for
from funnel.models import (db, Profile, ProposalSpace, SyncEvent, SyncTicketType, SyncTicket, SyncAttendee)
import csv
from urlparse import urlparse

init_for('dev')


class ExplaraTicket(object):
    def __init__(self, row):
        self.row = row

    def get(self, attr):
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
        return self.row[attrs[attr]]


def format_twitter(twitter_id):
    # formats a user given twitter handle
    # Eg: https://twitter.com/shreyas_satish -> shreyas_satish
    # @shreyas_satish -> shreyas_satish
    parsed_id = urlparse(str(twitter_id))
    return parsed_id.path.replace('/', '').replace('@', '')


def sync_ticket_types(ticket_types, space_id):
    for tt in ticket_types:
        stt = SyncTicketType.query.filter_by(name=tt, proposal_space_id=space_id).first()
        if not stt:
            stt = SyncTicketType(name=tt, proposal_space_id=space_id)
            db.session.add(stt)
    db.session.commit()


def sync_events(events, space_id):
    for e in events:
        se = SyncEvent.query.filter_by(name=e['name'], proposal_space_id=space_id).first()
        if not se:
            se = SyncEvent(name=e['name'], proposal_space_id=space_id)
            db.session.add(se)
            db.session.commit()
        for tt in e['ticket_types']:
            if tt not in [ticket_type.name for ticket_type in se.sync_ticket_types]:
                se.sync_ticket_types.append(SyncTicketType.query.filter_by(name=tt).first())
    db.session.commit()


def get_tickets(csv_file):
    tickets = []
    with open(csv_file, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)
        for row in reader:
            tickets.append(row)
    return tickets


def sync_tickets(proposal_space_id, csv_file):
    tickets = get_tickets(csv_file)

    for item in tickets:
        et = ExplaraTicket(item)
        ticket_type = SyncTicketType.query.filter_by(name=et.get('ticket_type'), proposal_space_id=proposal_space_id).first()
        ticket = SyncTicket.query.filter_by(ticket_no=et.get('ticket_no')).first()
        if not ticket:
            ticket = SyncTicket(
                ticket_no=et.get('ticket_no'),
                order_no=et.get('order_no'),
                attendee_name=et.get('fullname'),
                attendee_email=et.get('email'),
                attendee_phone=et.get('phone'),
                attendee_twitter=format_twitter(et.get('twitter')),
                attendee_job_title=et.get('job_title'),
                attendee_company=et.get('company'),
                attendee_city=et.get('city'),
                sync_ticket_type=ticket_type
                )
            db.session.add(ticket)
            db.session.commit()
        for e in ticket_type.sync_events:
            sa = SyncAttendee.query.filter_by(sync_ticket_id=ticket.id, sync_event_id=e.id).first()
            if not sa:
                sa = SyncAttendee(sync_ticket_id=ticket.id, sync_event_id=e.id)
                db.session.add(sa)
                db.session.commit()


def sync_metarefresh(csv_file):
    mr_profile = Profile.query.filter_by(name='metarefresh').first()
    mr_space = ProposalSpace.query.filter_by(name='2015').filter_by(profile_id=mr_profile.id).first()
    mr_ticket_types = ["ReactJS Workshop", "Performance audit workshop", "Offline registrations for ReactJS workshop", "Offline registrations for Performance Audit workshop", "T-shirt", "Super early geek", "Early geek", "Regular", "Late", "Offline registrations and payment", "Single day pass - 16th April", "Single day pass - 17th April"]
    mr_events = [
        {'name': 'MetaRefresh Day 1', 'ticket_types': ["Super early geek", "Early geek", "Regular", "Late", "Offline registrations and payment", "Single day pass - 16th April"]},
        {'name': 'MetaRefresh Day 2', 'ticket_types': ["Super early geek", "Early geek", "Regular", "Late", "Offline registrations and payment", "Single day pass - 17th April"]},
        {'name': 'ReactJS Workshop', 'ticket_types': ["ReactJS Workshop", "Offline registrations for ReactJS workshop"]},
        {'name': 'Performance Audit Workshop', 'ticket_types': ["Performance audit workshop", "Offline registrations for Performance Audit workshop"]},
    ]

    sync_ticket_types(mr_ticket_types, mr_space.id)
    sync_events(mr_events, mr_space.id)
    sync_tickets(mr_space.id, csv_file)
