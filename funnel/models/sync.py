# -*- coding: utf-8 -*-

from . import db, BaseMixin
from .space import ProposalSpace
from coaster import newsecret

__all__ = ['SyncEvent', 'SyncTicketType', 'SyncEventTicketType', 'SyncTicket', 'SyncAttendee']


def ticket_secret():
    # 8-character string sliced from newsecret
    return newsecret()[0:8]


class SyncEventTicketType(BaseMixin, db.Model):
    __tablename__ = 'sync_event_ticket_type'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    sync_event_id = db.Column(None, db.ForeignKey('sync_event.id'), nullable=False, primary_key=True)
    sync_ticket_type_id = db.Column(None, db.ForeignKey('sync_ticket_type.id'), nullable=False, primary_key=True)


class SyncEvent(BaseMixin, db.Model):
    __tablename__ = 'sync_event'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.Unicode(80), nullable=True)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('sync_events', cascade='all, delete-orphan', lazy='dynamic'))
    sync_ticket_types = db.relationship("SyncTicketType", secondary=SyncEventTicketType.__tablename__)


class SyncTicketType(BaseMixin, db.Model):
    __tablename__ = 'sync_ticket_type'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.Unicode(80), nullable=True)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('sync_ticket_types', cascade='all, delete-orphan', lazy='dynamic'))
    sync_events = db.relationship("SyncEvent", secondary=SyncEventTicketType.__tablename__)
    skip_list = ['T-shirt']


class SyncTicket(BaseMixin, db.Model):
    __tablename__ = 'sync_ticket'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    ticket_no = db.Column(db.Unicode(80), nullable=True, unique=True)
    order_no = db.Column(db.Unicode(80), nullable=True)
    attendee_name = db.Column(db.Unicode(80), nullable=True)
    #: Unvalidated email address
    attendee_email = db.Column(db.Unicode(80), nullable=True)
    #: Unvalidated phone number
    attendee_phone = db.Column(db.Unicode(80), nullable=True)
    #: Unvalidated Twitter id
    attendee_twitter = db.Column(db.Unicode(80), nullable=True)
    #: Job title
    attendee_job_title = db.Column(db.Unicode(80), nullable=True)
    #: Company
    attendee_company = db.Column(db.Unicode(80), nullable=True)
    #: Participant's city
    attendee_city = db.Column(db.Unicode(80), nullable=True)
    #: Access key for connecting to the user record (nulled when linked)
    attendee_access_key = db.Column(db.Unicode(44), nullable=True, default=ticket_secret, unique=True)
    sync_ticket_type_id = db.Column(None, db.ForeignKey('sync_ticket_type.id'), nullable=False, primary_key=True)
    sync_ticket_type = db.relationship(SyncTicketType,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan', lazy='dynamic'))


class SyncAttendee(BaseMixin, db.Model):
    __tablename__ = 'sync_attendee'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    sync_ticket_id = db.Column(None, db.ForeignKey('sync_ticket.id'), nullable=False, primary_key=True)
    sync_event_id = db.Column(None, db.ForeignKey('sync_event.id'), nullable=False, primary_key=True)
    sync_event = db.relationship(SyncEvent,
        backref=db.backref('sync_attendees', cascade='all, delete-orphan', lazy='dynamic'))
