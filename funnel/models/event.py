# -*- coding: utf-8 -*-
from . import db, BaseMixin
from .space import ProposalSpace
from .user import User
import random
import uuid
from sqlalchemy.ext.associationproxy import association_proxy
from datetime import datetime

__all__ = ['Event', 'TicketType', 'Participant', 'Attendee', 'SyncTicket']

PRINTABLE_ASCII = map(chr, range(32, 127))


def make_key():
    key = str(uuid.uuid4()).replace('-', '')
    return ''.join(random.sample(key, len(key)))


def make_public_key():
    return make_key()[:8]


def make_private_key():
    return make_key()[:8]


event_ticket_type = db.Table('event_ticket_type', db.Model.metadata,
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('ticket_type_id', db.Integer, db.ForeignKey('ticket_type.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False)
)


class Event(BaseMixin, db.Model):
    """ A discrete event under a proposal space.
        For instance, a space could be associated with a workshop and a two-day conference.
        The workshop constitutes as one event and each day of the conference
        constitutes as an independent event.
        This is done to allow distinguishing participants based on
        on the tickets they have, given a participant may have a ticket
        for only the workshop or a single day of the conference.
        An event is associated with multiple ticket types,
        which helps make the distinction between participants
    """
    __tablename__ = 'event'

    name = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('events', cascade='all, delete-orphan', lazy='dynamic'))
    ticket_types = db.relationship("TicketType", secondary=event_ticket_type, lazy='dynamic')
    participants = association_proxy('attendees', 'participant')


class TicketType(BaseMixin, db.Model):
    """ Models different types of tickets. Eg: Early Geek, Super Early Geek, Workshop A.
        A ticket type is associated with multiple events.
    """
    __tablename__ = 'ticket_type'

    name = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_types', cascade='all, delete-orphan', lazy='dynamic'))
    events = db.relationship("Event", secondary=event_ticket_type)


class Participant(BaseMixin, db.Model):
    """ Model users participating in the proposal space
        as an attendee, speaker, volunteer, sponsor.
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
    #: Access key for connecting to the user record
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
        db.session.commit()

    @classmethod
    def attendees_by_event(cls, event):
        participant_attendee_join = db.join(Participant, Attendee, Participant.id == Attendee.participant_id)
        stmt = db.select([Participant.id, Participant.fullname, Participant.email, Participant.company, Participant.twitter, Participant.puk, Participant.key, Attendee.checked_in]).select_from(participant_attendee_join).where(Attendee.event_id == event.id).order_by(Participant.fullname)
        return db.session.execute(stmt).fetchall()
    __table_args__ = (db.UniqueConstraint("email", "proposal_space_id"), {})


class Attendee(BaseMixin, db.Model):
    """ Join model between Participant and Event
    """
    __tablename__ = 'attendee'

    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False)
    participant = db.relationship(Participant,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False)
    event = db.relationship(Event,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    checked_in = db.Column(db.Boolean, default=False, nullable=False)


class SyncTicket(BaseMixin, db.Model):
    """ Model a ticket that was bought elsewhere. Eg: Explara
    """
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

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'ticket_no'),)

    @classmethod
    def tickets_from_space(cls, space_id):
        return cls.query.join(TicketType).filter_by(proposal_space_id=space_id).all()
