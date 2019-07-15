# -*- coding: utf-8 -*-

import base64
import os

from . import BaseMixin, BaseScopedNameMixin, db, with_roles
from .project import Project
from .user import User

__all__ = ['Event', 'TicketType', 'Participant', 'Attendee', 'SyncTicket', 'TicketClient']


def make_key():
    return unicode(base64.urlsafe_b64encode(os.urandom(128)))


def make_public_key():
    return make_key()[:8]


def make_private_key():
    return make_key()[:8]


event_ticket_type = db.Table('event_ticket_type', db.Model.metadata,
    db.Column('event_id', None, db.ForeignKey('event.id'), primary_key=True),
    db.Column('ticket_type_id', None, db.ForeignKey('ticket_type.id'), primary_key=True),
    db.Column('created_at', db.TIMESTAMP(timezone=True), default=db.func.utcnow(), nullable=False)
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
    A discrete event under a project.
    For instance, a project could be associated with a workshop and a two-day conference.
    The workshop constitutes as one event and each day of the conference
    constitutes as an independent event.
    This is done to allow distinguishing participants based on
    on the tickets they have, given a participant may have a ticket
    for only the workshop or a single day of the conference.
    An event is associated with multiple ticket types,
    which helps make the distinction between participants.
    """
    __tablename__ = 'event'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project,
        backref=db.backref('events', cascade='all, delete-orphan'))
    parent = db.synonym('project')
    ticket_types = db.relationship('TicketType', secondary=event_ticket_type)
    participants = db.relationship('Participant', secondary='attendee', backref='events', lazy='dynamic')
    badge_template = db.Column(db.Unicode(250), nullable=True)
    __table_args__ = (db.UniqueConstraint('project_id', 'name'), db.UniqueConstraint('project_id', 'title'))


class TicketType(ScopedNameTitleMixin, db.Model):
    """
    Models different types of tickets. Eg: Early Geek, Super Early Geek, Workshop A.
    A ticket type is associated with multiple events.
    """
    __tablename__ = 'ticket_type'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project,
        backref=db.backref('ticket_types', cascade='all, delete-orphan'))
    parent = db.synonym('project')
    events = db.relationship('Event', secondary=event_ticket_type)
    __table_args__ = (db.UniqueConstraint('project_id', 'name'), db.UniqueConstraint('project_id', 'title'))


class Participant(BaseMixin, db.Model):
    """
    Model users participating in one or multiple events.
    """
    __tablename__ = 'participant'

    fullname = with_roles(db.Column(db.Unicode(80), nullable=False),
        read={'concierge', 'subject', 'scanner'})
    #: Unvalidated email address
    email = with_roles(db.Column(db.Unicode(254), nullable=False),
        read={'concierge', 'subject', 'scanner'})
    #: Unvalidated phone number
    phone = with_roles(db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'})
    #: Unvalidated Twitter id
    twitter = with_roles(db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'})
    #: Job title
    job_title = with_roles(db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'})
    #: Company
    company = with_roles(db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'})
    #: Participant's city
    city = with_roles(db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'})
    # public key
    puk = db.Column(db.Unicode(44), nullable=False, default=make_public_key, unique=True)
    key = db.Column(db.Unicode(44), nullable=False, default=make_private_key, unique=True)
    badge_printed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, backref=db.backref('participants', cascade='all, delete-orphan'))
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(Project, backref=db.backref('participants', cascade='all, delete-orphan')),
        read={'concierge', 'subject', 'scanner'})

    __table_args__ = (db.UniqueConstraint('project_id', 'email'),)

    def roles_for(self, actor, anchors=()):
        roles = super(Participant, self).roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('subject')
        cx = ContactExchange.query.get((actor.id, self.id))
        if cx is not None:
            roles.add('scanner')
        return roles

    @classmethod
    def get(cls, current_project, current_email):
        return cls.query.filter_by(project=current_project, email=current_email).one_or_none()

    @classmethod
    def upsert(cls, current_project, current_email, **fields):
        participant = cls.get(current_project, current_email)
        if participant:
            participant._set_fields(fields)
        else:
            participant = cls(project=current_project, email=current_email, **fields)
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
        """
        participant_list = db.session.query('id', 'fullname', 'email', 'company', 'twitter', 'puk', 'key', 'checked_in', 'badge_printed', 'ticket_type_titles').from_statement(db.text('''
            SELECT distinct(participant.id), participant.fullname, participant.email, participant.company, participant.twitter, participant.puk, participant.key, attendee.checked_in, participant.badge_printed,
            (SELECT string_agg(title, ',') FROM sync_ticket INNER JOIN ticket_type ON sync_ticket.ticket_type_id = ticket_type.id where sync_ticket.participant_id = participant.id) AS ticket_type_titles
            FROM participant INNER JOIN attendee ON participant.id = attendee.participant_id LEFT OUTER JOIN sync_ticket ON participant.id = sync_ticket.participant_id
            WHERE attendee.event_id = :event_id
            ORDER BY participant.fullname
        ''')).params(event_id=event.id).all()
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
    def get(cls, event, participant_id):
        return cls.query.filter_by(event=event, participant_id=participant_id).one_or_none()


class TicketClient(BaseMixin, db.Model):
    __tablename__ = 'ticket_client'
    name = db.Column(db.Unicode(80), nullable=False)
    client_eventid = db.Column(db.Unicode(80), nullable=False)
    clientid = db.Column(db.Unicode(80), nullable=False)
    client_secret = db.Column(db.Unicode(80), nullable=False)
    client_access_token = db.Column(db.Unicode(80), nullable=False)
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project,
        backref=db.backref('ticket_clients', cascade='all, delete-orphan'))

    def import_from_list(self, ticket_list):
        """
        Batch upserts the tickets and its associated ticket types and participants.
        Cancels the tickets in cancel_list.
        """
        for ticket_dict in ticket_list:
            ticket_type = TicketType.upsert(self.project, current_title=ticket_dict['ticket_type'])

            participant = Participant.upsert(self.project, ticket_dict['email'],
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
    ticket_client_id = db.Column(None, db.ForeignKey('ticket_client.id'), nullable=False)
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


# Import symbols required only in functions at bottom of file to avoid
# cyclic dependency failures.
from .contact_exchange import ContactExchange  # isort:skip
