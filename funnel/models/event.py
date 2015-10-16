# -*- coding: utf-8 -*-
import os
import base64
from datetime import datetime
from sqlalchemy import or_
from . import db, BaseMixin, BaseScopedNameMixin
from .space import ProposalSpace
from .user import User

__all__ = ['Event', 'TicketType', 'Participant', 'Attendee', 'SyncTicket', 'TicketClient']


def make_key():
    return base64.urlsafe_b64encode(os.urandom(128))


def make_public_key():
    return make_key()[:8]


def make_private_key():
    return make_key()[:8]


event_ticket_type = db.Table('event_ticket_type', db.Model.metadata,
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('ticket_type_id', db.Integer, db.ForeignKey('ticket_type.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False)
    )


class Event(BaseScopedNameMixin, db.Model):
    """
    A discrete event under a proposal space.
    For instance, a space could be associated with a workshop and a two-day conference.
    The workshop constitutes as one event and each day of the conference
    constitutes as an independent event.
    This is done to allow distinguishing participants based on
    on the tickets they have, given a participant may have a ticket
    for only the workshop or a single day of the conference.
    An event is associated with multiple ticket types,
    which helps make the distinction between participants.
    """
    __tablename__ = 'event'

    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('events', cascade='all, delete-orphan'))
    parent = db.synonym('proposal_space')
    ticket_types = db.relationship('TicketType', secondary=event_ticket_type)
    participants = db.relationship('Participant', secondary='attendee', backref='events', lazy='dynamic')
    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'name'), db.UniqueConstraint('proposal_space_id', 'title'))

    @classmethod
    def get(cls, space, name_or_title):
        return cls.query.filter_by(proposal_space=space)\
            .filter(or_(cls.name == name_or_title, cls.title == name_or_title)).one_or_none()

    @classmethod
    def upsert(cls, space, name_or_title, **fields):
        event = cls.get(space, name_or_title)
        if event:
            event._set_fields(fields)
        else:
            fields.pop('proposal_space', None)
            fields.pop('title', None)
            event = cls(proposal_space=space, title=name_or_title, **fields)
            db.session.add(event)
        return event


class TicketType(BaseScopedNameMixin, db.Model):
    """
    Models different types of tickets. Eg: Early Geek, Super Early Geek, Workshop A.
    A ticket type is associated with multiple events.
    """
    __tablename__ = 'ticket_type'

    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_types', cascade='all, delete-orphan'))
    parent = db.synonym('proposal_space')
    events = db.relationship('Event', secondary=event_ticket_type)
    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'name'), db.UniqueConstraint('proposal_space_id', 'title'))

    @classmethod
    def get(cls, space, name_or_title):
        return cls.query.filter_by(proposal_space=space)\
            .filter(or_(cls.name == name_or_title, cls.title == name_or_title)).one_or_none()

    @classmethod
    def upsert(cls, space, name_or_title, **fields):
        ticket_type = cls.get(space, name_or_title)
        if ticket_type:
            ticket_type._set_fields(fields)
        else:
            fields.pop('proposal_space', None)
            fields.pop('title', None)
            ticket_type = cls(proposal_space=space, title=name_or_title, **fields)
            db.session.add(ticket_type)
        return ticket_type


class Participant(BaseMixin, db.Model):
    """
    Model users participating in one or multiple events.
    """
    __tablename__ = 'participant'

    fullname = db.Column(db.Unicode(80), nullable=False)
    #: Unvalidated email address
    email = db.Column(db.Unicode(254), nullable=False)
    #: Unvalidated phone number
    phone = db.Column(db.Unicode(80), nullable=True)
    #: Unvalidated Twitter id
    twitter = db.Column(db.Unicode(80), nullable=True)
    #: Job title
    job_title = db.Column(db.Unicode(80), nullable=True)
    #: Company
    company = db.Column(db.Unicode(80), nullable=True)
    #: Participant's city
    city = db.Column(db.Unicode(80), nullable=True)
    # public key
    puk = db.Column(db.Unicode(44), nullable=False, default=make_public_key, unique=True)
    key = db.Column(db.Unicode(44), nullable=False, default=make_private_key, unique=True)
    badge_printed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, backref=db.backref('participants', cascade='all, delete-orphan'))
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('participants', cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'email'),)

    @classmethod
    def get(cls, space, email):
        return cls.query.filter_by(proposal_space=space, email=email).one_or_none()

    @classmethod
    def upsert(cls, space, emailid, **fields):
        participant = cls.get(space, emailid)
        if participant:
            participant._set_fields(fields)
        else:
            fields.pop('proposal_space', None)
            fields.pop('email', None)
            participant = cls(proposal_space=space, email=emailid, **fields)
            db.session.add(participant)
        return participant

    def add_events(self, events):
        for event in events:
            if event not in self.events:
                self.events.append(event)

    def remove_events(self, events):
        for event in events:
            if event in self.events:
                self.events.remove(event)


class Attendee(BaseMixin, db.Model):
    """
    Join model between Participant and Event.
    TODO: #140 - Rename Attendee to EventParticipant
    """
    __tablename__ = 'attendee'

    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False)
    participant = db.relationship(Participant,
        backref=db.backref('attendees', cascade='all, delete-orphan'))
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False)
    event = db.relationship(Event,
        backref=db.backref('attendees', cascade='all, delete-orphan'))
    checked_in = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint('event_id', 'participant_id'),)


class TicketClient(BaseMixin, db.Model):
    __tablename__ = 'ticket_client'
    name = db.Column(db.Unicode(80), nullable=False)
    client_eventid = db.Column(db.Unicode(80), nullable=False)
    clientid = db.Column(db.Unicode(80), nullable=False)
    client_secret = db.Column(db.Unicode(80), nullable=False)
    client_access_token = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_clients', cascade='all, delete-orphan'))

    def import_from_list(self, space, ticket_list, cancel_list=[]):
        """
        Batch upserts the tickets and its associated ticket types and participants.
        Cancels the tickets in cancel_list.
        """
        for ticket in cancel_list:
            ticket.participant.remove_events(ticket.ticket_type.events)

        for ticket_dict in ticket_list:
            ticket_type = TicketType.upsert(space, ticket_dict['ticket_type'],
                            title=ticket_dict['ticket_type'], proposal_space=space)

            participant = Participant.upsert(space, ticket_dict['email'],
                             email=ticket_dict['email'],
                             fullname=ticket_dict['fullname'],
                             phone=ticket_dict['phone'],
                             twitter=ticket_dict['twitter'],
                             company=ticket_dict['company'],
                             city=ticket_dict['city']
                            )

            ticket = SyncTicket.upsert(self, ticket_dict.get('order_no'), ticket_dict.get('ticket_no'),
                participant=participant, ticket_type=ticket_type)

            if ticket.previous_participant:
                # Remove previous participant's access to events
                ticket.previous_participant.remove_events(ticket_type.events)

            # Ensure that the new or updated participant has access to events
            ticket.participant.add_events(ticket_type.events)


class SyncTicket(BaseMixin, db.Model):
    """ Model for a ticket that was bought elsewhere. Eg: Explara."""
    __tablename__ = 'sync_ticket'

    ticket_no = db.Column(db.Unicode(80), nullable=False)
    order_no = db.Column(db.Unicode(80), nullable=False)
    ticket_type_id = db.Column(None, db.ForeignKey('ticket_type.id'), nullable=False)
    ticket_type = db.relationship(TicketType,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan'))
    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False)
    participant = db.relationship(Participant, primaryjoin=participant_id == Participant.id,
        backref=db.backref('sync_tickets', cascade="all, delete-orphan"))
    ticket_client_id = db.Column(db.Integer, db.ForeignKey('ticket_client.id'), nullable=False)
    ticket_client = db.relationship(TicketClient,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan'))
    __table_args__ = (db.UniqueConstraint('ticket_client_id', 'order_no', 'ticket_no'),)

    previous_participant = None

    @classmethod
    def get(cls, ticket_client, order_no, ticket_no):
        return cls.query.filter_by(ticket_client=ticket_client, order_no=order_no, ticket_no=ticket_no).one_or_none()

    @classmethod
    def upsert(cls, ticket_client, order_no, ticket_no, **fields):
        """
        Returns a tuple containing the upserted ticket, and the participant the ticket
        was previously associated with or None if there was no earlier participant.
        """
        ticket = cls.get(ticket_client, order_no, ticket_no)
        if ticket:
            if ticket.participant is not fields.get('participant'):
                # Transfer ticket
                ticket.previous_participant = ticket.participant
            ticket._set_fields(fields)
        else:
            fields.pop('ticket_client', None)
            fields.pop('order_no', None)
            fields.pop('ticket_no', None)
            ticket = SyncTicket(ticket_client=ticket_client, order_no=order_no, ticket_no=ticket_no, **fields)
            db.session.add(ticket)

        return ticket

    @classmethod
    def exclude(cls, space, ticket_client, ticket_nos):
        return cls.query.filter_by(proposal_space=space, ticket_client=ticket_client
            ).filter(~cls.ticket_no.in_(ticket_nos))
