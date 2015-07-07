# -*- coding: utf-8 -*-
import os
import base64
import logging
from datetime import datetime
from sqlalchemy.ext.associationproxy import association_proxy
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
        backref=db.backref('events', cascade='all, delete-orphan', lazy='dynamic'))
    parent = db.synonym('proposal_space')
    ticket_types = db.relationship("TicketType", secondary=event_ticket_type, lazy='dynamic')
    participants = association_proxy('attendees', 'participant')
    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'name'),)

    @classmethod
    def get(cls, title, space, create=False):
        event = cls.query.filter_by(title=title, proposal_space=space).first()
        if not event and create:
            event = cls(title=title, proposal_space=space)
            db.session.add(event)
        return event

    @classmethod
    def sync_from_list(cls, event_list, space):
        for event_dict in event_list:
            event = cls.get(event_dict.get('name'), space, create=True)
            for ticket_type_name in event_dict.get('ticket_types', []):
                if ticket_type_name not in [ticket_type.name for ticket_type in event.ticket_types]:
                    event.ticket_types.append(TicketType.get(ticket_type_name, space, create=True))


class TicketType(BaseMixin, db.Model):
    """
    Models different types of tickets. Eg: Early Geek, Super Early Geek, Workshop A.
    A ticket type is associated with multiple events.
    """
    __tablename__ = 'ticket_type'

    name = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_types', cascade='all, delete-orphan', lazy='dynamic'))
    events = db.relationship("Event", secondary=event_ticket_type)

    @classmethod
    def get(cls, name, space, create=False):
        ticket_type = cls.query.filter_by(name=name, proposal_space=space).first()
        if not ticket_type and create:
            ticket_type = cls(name=name, proposal_space=space)
            db.session.add(ticket_type)
        return ticket_type


class Participant(BaseMixin, db.Model):
    """
    Model users participating in the proposal space
    as an attendee, speaker, volunteer, sponsor etc .
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
        backref=db.backref('participants', cascade='all, delete-orphan', lazy='dynamic'))
    events = db.relationship(Event, secondary='attendee')

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'email'),)

    @classmethod
    def update_badge_printed(cls, event, badge_printed):
        participant_ids = [participant.id for participant in event.participants]
        db.session.query(cls).filter(cls.id.in_(participant_ids)).update({'badge_printed': badge_printed}, False)

    @classmethod
    def attendees_by_event(cls, event):
        participant_attendee_join = db.join(Participant, Attendee, Participant.id == Attendee.participant_id)
        stmt = db.select([Participant.id, Participant.fullname, Participant.email, Participant.company, Participant.twitter, Participant.puk, Participant.key, Attendee.checked_in, Participant.badge_printed]).select_from(participant_attendee_join).where(Attendee.event_id == event.id).order_by(Participant.fullname)
        return db.session.execute(stmt).fetchall()

    @classmethod
    def make_from_dict(cls, participant_dict, space):
        return Participant(
            fullname=participant_dict.get('fullname'),
            email=participant_dict.get('email'),
            phone=participant_dict.get('phone'),
            twitter=participant_dict.get('twitter'),
            job_title=participant_dict.get('job_title'),
            company=participant_dict.get('company'),
            city=participant_dict.get('city'),
            proposal_space=space
        )


class Attendee(BaseMixin, db.Model):
    """Join model between Participant and Event."""
    __tablename__ = 'attendee'

    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False)
    participant = db.relationship(Participant,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False)
    event = db.relationship(Event,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    checked_in = db.Column(db.Boolean, default=False, nullable=False)


class TicketClient(BaseMixin, db.Model):
    __tablename__ = 'ticket_client'
    name = db.Column(db.Unicode(80), nullable=False)
    client_event_id = db.Column(db.Unicode(80), nullable=False)
    client_id = db.Column(db.Unicode(80), nullable=False)
    client_secret = db.Column(db.Unicode(80), nullable=False)
    client_access_token = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_clients', cascade='all, delete-orphan', lazy='dynamic'))


class SyncTicket(BaseMixin, db.Model):
    """ Model for a ticket that was bought elsewhere. Eg: Explara."""
    __tablename__ = 'sync_ticket'

    ticket_no = db.Column(db.Unicode(80), nullable=False)
    order_no = db.Column(db.Unicode(80), nullable=False)
    ticket_type_id = db.Column(None, db.ForeignKey('ticket_type.id'), nullable=False)
    ticket_type = db.relationship(TicketType,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan', lazy='dynamic'))
    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False)
    participant = db.relationship(Participant, primaryjoin=participant_id == Participant.id,
        backref=db.backref('sync_tickets', cascade="all, delete-orphan"))
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan', lazy='dynamic'))
    ticket_client_id = db.Column(db.Integer, db.ForeignKey('ticket_client.id'), nullable=False)
    ticket_client = db.relationship(TicketClient,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'order_no', 'ticket_no'),)

    @classmethod
    def fetch(cls, ticket_no, order_no, space):
        return cls.query.filter_by(ticket_no=ticket_no, order_no=order_no, proposal_space=space).first()

    @classmethod
    def sync_from_list(cls, ticket_list, space, ticket_client=None):
        # track current ticket nos
        current_ticket_ids = []
        for ticket_dict in ticket_list:
            ticket = SyncTicket.fetch(ticket_dict.get('ticket_no'), ticket_dict.get('order_no'), space)
            ticket_ticket_type = TicketType.query.filter_by(name=ticket_dict.get('ticket_type'), proposal_space=space).first()
            # get or create participant
            ticket_participant = Participant.query.filter_by(email=ticket_dict.get('email'), proposal_space=space).first()
            if not ticket_participant:
                # create a new participant record if required
                ticket_participant = Participant.make_from_dict(ticket_dict, space)
                db.session.add(ticket_participant)

            if ticket:
                # check if participant has changed
                if ticket.participant is not ticket_participant:
                    # update the participant record attached to the ticket
                    ticket.participant = ticket_participant
            else:
                ticket = SyncTicket(
                    ticket_no=ticket_dict.get('ticket_no'),
                    order_no=ticket_dict.get('order_no'),
                    ticket_type=ticket_ticket_type,
                    participant=ticket_participant,
                    ticket_client=ticket_client,
                    proposal_space=space
                )
                db.session.add(ticket)
            current_ticket_ids.append(ticket.id)
            if ticket.ticket_type:
                for event in ticket.ticket_type.events:
                    a = Attendee.query.filter_by(event_id=event.id, participant_id=ticket.participant.id).first()
                    if not a:
                        a = Attendee(event_id=event.id, participant_id=ticket.participant.id)
                        db.session.add(a)

        # sweep cancelled tickets
        cancelled_tickets = SyncTicket.query.filter_by(proposal_space=space).filter(~SyncTicket.id.in_(current_ticket_ids)).all()
        logging.warn("Sweeping cancelled tickets..")
        for ct in cancelled_tickets:
            logging.warn("Removing event access for {0}".format(ct.participant.email))
            st = SyncTicket.fetch(ct.ticket_no, ct.order_no, space)
            event_ids = [event.id for event in st.ticket_type.events]
            cancelled_attendees = Attendee.query.filter(Attendee.participant_id == st.participant.id).filter(Attendee.event_id.in_(event_ids)).all()
            for ca in cancelled_attendees:
                db.session.delete(ca)
            db.session.delete(st)
