# -*- coding: utf-8 -*-
import os
import base64
from datetime import datetime
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
    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'name'),)

    @classmethod
    def get(cls, space, title):
        return cls.query.filter_by(title=title, proposal_space=space).first()

    @classmethod
    def create_from(cls, space, title):
        event = cls(title=title, proposal_space=space)
        db.session.add(event)
        return event

    @classmethod
    def get_or_create_from(cls, space, title):
        event = cls.get(space, title)
        if not event:
            event = cls.create_from(space, title)
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
    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'name'),)

    @classmethod
    def get(cls, space, title):
        return cls.query.filter_by(title=title, proposal_space=space).first()

    @classmethod
    def create_from(cls, space, title, events=[]):
        ticket_type = cls(
            title=title,
            proposal_space=space,
            events=events
        )
        db.session.add(ticket_type)
        return ticket_type

    @classmethod
    def get_or_create_from(cls, space, title, events=[]):
        ticket_type = TicketType.get(space, title)
        if not ticket_type:
            ticket_type = TicketType.create_from(space, title, events)
        return ticket_type


class Participant(BaseMixin, db.Model):
    """
    Model users participating in one or multiple events.
    """
    __tablename__ = 'participant'

    fullname = db.Column(db.Unicode(80), nullable=False)
    #: Unvalidated email address
    email = db.Column(db.Unicode(80), nullable=False)
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
        return cls.query.filter_by(proposal_space=space, email=email).first()

    @classmethod
    def create_from(cls, space, email, fields):
        participant = cls(
            fullname=fields.get('fullname'),
            email=email,
            phone=fields.get('phone'),
            twitter=fields.get('twitter'),
            job_title=fields.get('job_title'),
            company=fields.get('company'),
            city=fields.get('city'),
            events=fields.get('events', []),
            proposal_space=space
        )
        db.session.add(participant)
        return participant

    @classmethod
    def get_or_create_from(cls, space, email, fields):
        participant = Participant.get(space, email)
        if not participant:
            participant = Participant.create_from(space, email, fields)
        return participant


class Attendee(BaseMixin, db.Model):
    """Join model between Participant and Event."""
    __tablename__ = 'attendee'

    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False)
    participant = db.relationship(Participant,
        backref=db.backref('attendees', cascade='all, delete-orphan'))
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False)
    event = db.relationship(Event,
        backref=db.backref('attendees', cascade='all, delete-orphan'))
    checked_in = db.Column(db.Boolean, default=False, nullable=False)

    @classmethod
    def get(cls, participant, event):
        return cls.query.filter_by(participant=participant, event=event).first()


class TicketClient(BaseMixin, db.Model):
    __tablename__ = 'ticket_client'
    name = db.Column(db.Unicode(80), nullable=False)
    client_event_id = db.Column(db.Unicode(80), nullable=False)
    client_id = db.Column(db.Unicode(80), nullable=False)
    client_secret = db.Column(db.Unicode(80), nullable=False)
    client_access_token = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_clients', cascade='all, delete-orphan'))


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
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan'))
    ticket_client_id = db.Column(db.Integer, db.ForeignKey('ticket_client.id'), nullable=False)
    ticket_client = db.relationship(TicketClient,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'order_no', 'ticket_no'),)

    @classmethod
    def get(cls, space, order_no, ticket_no):
        return cls.query.filter_by(ticket_no=ticket_no, order_no=order_no, proposal_space=space).first()

    @classmethod
    def create_from(cls, space, order_no, ticket_no, ticket_type, participant, ticket_client):
        ticket = cls(
            proposal_space=space,
            order_no=order_no,
            ticket_no=ticket_no,
            ticket_type=ticket_type,
            participant=participant,
            ticket_client=ticket_client,
        )
        db.session.add(ticket)
        return ticket
