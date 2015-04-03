#!/usr/bin/env python

from flask import *
from funnel import init_for
from funnel.models import (db, Profile, ProposalSpace, Event, TicketType, SyncTicket, Attendee)
import csv
from urlparse import urlparse

init_for('dev')


class ExplaraTicket(object):
    # model of an explara ticket obtained from their CSV
    def __init__(self, row):
        self.row = row

    def get(self, attr):
        # returns the value of the requested attributed by
        # referring to a map of attributes and their respective column
        # indexes in the CSV
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
    # Eg: https://twitter.com/shreyas_satish -> shreyas_satish, @shreyas_satish -> shreyas_satish
    return urlparse(str(twitter_id)).path.replace('/', '').replace('@', '')


def sync_ticket_types(ticket_types, space_id):
    for tt in ticket_types:
        tt = TicketType.query.filter_by(name=tt, proposal_space_id=space_id).first()
        if not stt:
            tt = TicketType(name=tt, proposal_space_id=space_id)
            db.session.add(tt)
    db.session.commit()


def sync_events(events, space_id):
    for e in events:
        e = Event.query.filter_by(name=e['name'], proposal_space_id=space_id).first()
        if not e:
            e = Event(name=e['name'], proposal_space_id=space_id)
            db.ession.add(e)
            db.ession.commit()
        for tt in e['ticket_types']:
            if tt not in [ticket_type.name for ticket_type in e.sync_ticket_types]:
                e.ticket_types.append(TicketType.query.filter_by(name=tt).first())
    db.session.commit()


def get_rows_from_csv(csv_file, skip_header=True):
    with open(csv_file, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        if skip_header:
            next(reader)
        return [row for row in reader]


def sync_tickets(proposal_space_id, csv_file):
    tickets = get_rows_from_csv(csv_file)

    for item in tickets:
        et = ExplaraTicket(item)
        ticket_type = TicketType.query.filter_by(name=et.get('ticket_type'), proposal_space_id=proposal_space_id).first()
        participant = Participant.query.filter_by(email=et.get('email')).first()
        ticket = SyncTicket.query.filter_by(ticket_no=et.get('ticket_no')).first()
        if ticket:
            participant.fullname = et.get('fullname')
            participant.email = et.get('email')
            participant.phone = et.get('phone')
            participant.twitter = et.get('twitter')
            participant.job_title = et.get('job_title')
            participant.company = et.get('company')
            participant.city = et.get('city')
            ticket.ticket_type = ticket_type
        else:
            participant = Participant(
                fullname=et.get('fullname'),
                email=et.get('email'),
                phone=et.get('phone'),
                twitter=et.get('twitter'),
                job_title=et.get('job_title'),
                company=et.get('company'),
                city=et.get('city')
            )
            db.session.add(participant)
            db.session.commit()
            ticket = SyncTicket(
                ticket_no=et.get('ticket_no'),
                order_no=et.get('order_no'),
                sync_ticket_type=ticket_type,
                participant=participant
                )
            db.session.add(ticket)
        db.session.commit()

    for e in space.events:
        a = Attendee.query.filter_by(event_id=e.id, participant_id=participant.id).query.first()
        if not a:
            a = Attendee(event_id=e.id, participant_id=participant.id)
        db.session.add(a)
        db.session.commit()


def sync_metarefresh(profile_name, space_name, csv_file):
    mr_profile = Profile.query.filter_by(name=profile_name).first()
    mr_space = ProposalSpace.query.filter_by(name=space_name).filter_by(profile_id=mr_profile.id).first()
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
    sync_attendees(mr_space)
