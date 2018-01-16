# -*- coding: utf-8 -*-
import os
import base64
from datetime import datetime
from sqlalchemy.sql import text
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


class ScopedNameTitleMixin(BaseScopedNameMixin):
    # TODO: Move this into coaster?
    @classmethod
    def get(cls, parent, current_name=None, current_title=None):
        if not bool(current_name) ^ bool(current_title):
            raise TypeError("Expects current_name xor current_title")
        if current_name:
            return cls.query.filter_by(parent=parent, name=current_name).one_or_none()
        else:
            return cls.query.filter_by(parent=parent, title=current_title).one_or_none()

    @classmethod
    def upsert(cls, parent, current_name=None, current_title=None, **fields):
        instance = cls.get(parent, current_name, current_title)
        if instance:
            instance._set_fields(fields)
        else:
            fields.pop('title', None)
            instance = cls(parent=parent, title=current_title, **fields)
            db.session.add(instance)
        return instance


class Event(ScopedNameTitleMixin, db.Model):
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


class TicketType(ScopedNameTitleMixin, db.Model):
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
    def get(cls, current_space, current_email):
        return cls.query.filter_by(proposal_space=current_space, email=current_email).one_or_none()

    @classmethod
    def upsert(cls, current_space, current_email, **fields):
        participant = cls.get(current_space, current_email)
        if participant:
            participant._set_fields(fields)
        else:
            participant = cls(proposal_space=current_space, email=current_email, **fields)
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

    @classmethod
    def checkin_list(cls, event):
        """
        Returns participant details along with their associated ticket types as a comma-separated string.
        WARNING: This query uses `string_agg` and hence will only work in PostgreSQL >= 9.0
        """
        participant_list = db.session.query('id', 'fullname', 'email', 'company', 'twitter', 'puk', 'key', 'checked_in', 'badge_printed', 'ticket_type_titles').from_statement(text('''
            SELECT distinct(participant.id), participant.fullname, participant.email, participant.company, participant.twitter, participant.puk, participant.key, attendee.checked_in, participant.badge_printed,
            (select string_agg(title, ',') from sync_ticket INNER JOIN ticket_type ON sync_ticket.ticket_type_id = ticket_type.id where sync_ticket.participant_id = participant.id) AS ticket_type_titles
            FROM participant INNER JOIN attendee ON participant.id = attendee.participant_id LEFT OUTER JOIN sync_ticket ON participant.id = sync_ticket.participant_id
            WHERE attendee.event_id = {event_id}
            ORDER BY participant.fullname
        '''.format(event_id=event.id))).all()
        return participant_list


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

    @classmethod
    def get(cls, event, participant):
        return cls.query.filter_by(event=event, participant=participant).one_or_none()


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

    def import_from_list(self, ticket_list):
        """
        Batch upserts the tickets and its associated ticket types and participants.
        Cancels the tickets in cancel_list.
        """
        for ticket_dict in ticket_list:
            ticket_type = TicketType.upsert(self.proposal_space, current_title=ticket_dict['ticket_type'])

            participant = Participant.upsert(self.proposal_space, ticket_dict['email'],
                             fullname=ticket_dict['fullname'],
                             phone=ticket_dict['phone'],
                             twitter=ticket_dict['twitter'],
                             company=ticket_dict['company'],
                             job_title=ticket_dict['job_title'],
                             city=ticket_dict['city']
                            )

            ticket = SyncTicket.get(self, ticket_dict.get('order_no'), ticket_dict.get('ticket_no'))
            if ticket and (ticket.participant is not participant or ticket_dict.get('status') == u'cancelled'):
                # Ensure that the participant of a transferred or cancelled ticket does not have access to
                # this ticket's events
                ticket.participant.remove_events(ticket_type.events)

            if ticket_dict.get('status') == u'confirmed':
                ticket = SyncTicket.upsert(self, ticket_dict.get('order_no'), ticket_dict.get('ticket_no'),
                    participant=participant, ticket_type=ticket_type)
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
            ticket._set_fields(fields)
        else:
            fields.pop('ticket_client', None)
            fields.pop('order_no', None)
            fields.pop('ticket_no', None)
            ticket = SyncTicket(ticket_client=ticket_client, order_no=order_no, ticket_no=ticket_no, **fields)

            db.session.add(ticket)

        return ticket
