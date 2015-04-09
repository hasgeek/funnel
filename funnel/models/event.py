# -*- coding: utf-8 -*-
from . import db, BaseMixin
from .space import ProposalSpace
from .user import User
import uuid
from .. import app
import qrcode
import qrcode.image.svg


__all__ = ['Event', 'TicketType', 'EventTicketType', 'Participant', 'Attendee', 'SyncTicket']


class EventTicketType(BaseMixin, db.Model):
    """ Join Model for Event and TicketType
    """
    __tablename__ = 'event_ticket_type'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False, primary_key=True)
    ticket_type_id = db.Column(None, db.ForeignKey('ticket_type.id'), nullable=False, primary_key=True)


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

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('events', cascade='all, delete-orphan', lazy='dynamic'))
    ticket_types = db.relationship("TicketType", secondary=EventTicketType.__tablename__)


class TicketType(BaseMixin, db.Model):
    """ Models different types of tickets. Eg: Early Geek, Super Early Geek, Workshop A.
        A ticket type is associated with multiple events.
    """
    __tablename__ = 'ticket_type'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.Unicode(80), nullable=False)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_types', cascade='all, delete-orphan', lazy='dynamic'))
    events = db.relationship("Event", secondary=EventTicketType.__tablename__)


class Participant(BaseMixin, db.Model):
    """ Model users participating in the proposal space
        as an attendee, speaker, volunteer, sponsor.
    """
    __tablename__ = 'participant'

    def make_key():
        # 8-character string sliced from uuid
        return str(uuid.uuid4())[0:8]

    fullname = db.Column(db.Unicode(80), nullable=True)
    #: Unvalidated email address
    email = db.Column(db.Unicode(80), nullable=False, unique=True)
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
    #: Access key for connecting to the user record
    key = db.Column(db.Unicode(44), nullable=True, default=make_key, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('participant', cascade="all, delete-orphan"))
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('participants', cascade='all, delete-orphan', lazy='dynamic'))

    @classmethod
    def get_by_event(cls, event):
        participant_attendee_join = db.join(Participant, Attendee, Participant.id == Attendee.participant_id)
        stmt = db.select([Participant.id, Participant.fullname, Participant.email, Participant.company, Participant.twitter, Attendee.checked_in]).select_from(participant_attendee_join).where(Attendee.event_id == event.id).order_by(Participant.fullname)
        return db.session.execute(stmt).fetchall()

    def split_name(self, fullname):
        """ Splits a given fullname into two parts
            a first name, and a concanetated last name.
            Eg: "ABC DEF EFG" -> ("ABC", "DEF EFG")
        """
        name_splits = fullname.split()
        first_name = name_splits[0]
        last_name = " ".join([s for s in name_splits[1:]])
        return first_name, last_name

    def format_twitter(self, twitter):
        return "@{0}".format(twitter) if twitter else ""

    def file_contents(self, path):
        """ Returns contents of a given file path
        """
        file = open(path)
        content = file.read()
        file.close()
        return content

    def make_qrcode(self, path):
        """ Makes a QR code with a given path and returns the raw svg
            Data Format is id:key. Eg: 1:xxxxxxxx
        """
        data = "{0}:{1}".format(str(self.id), self.key)
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(data, image_factory=factory)
        img.save(path)
        return self.file_contents(path)

    def make_qrcode_path(self, space):
        """ Returns a filepath. Set a config var for BADGES_PATH.
            Eg: static/badges/metarefresh_2015_1.svg
        """
        return "{0}/{1}_{2}_{3}.{4}".format(app.config.get('BADGES_PATH'), space.profile.name, space.name, str(self.id), 'svg')


class Attendee(BaseMixin, db.Model):
    """ Join model between Participant and Event
    """
    __tablename__ = 'attendee'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False, primary_key=True)
    participant = db.relationship(Participant,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False, primary_key=True)
    event = db.relationship(Event,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    checked_in = db.Column(db.Boolean, default=False, nullable=False)


class SyncTicket(BaseMixin, db.Model):
    """ Model a ticket that was bought elsewhere. Eg: Explara
    """
    __tablename__ = 'sync_ticket'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    ticket_no = db.Column(db.Unicode(80), nullable=False, unique=True)
    order_no = db.Column(db.Unicode(80), nullable=False)
    ticket_type_id = db.Column(None, db.ForeignKey('ticket_type.id'), nullable=False, primary_key=True)
    ticket_type = db.relationship(TicketType,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan', lazy='dynamic'))
    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False, primary_key=True)
    participant = db.relationship(Participant, primaryjoin=participant_id == Participant.id,
        backref=db.backref('sync_tickets', cascade="all, delete-orphan"))

    @classmethod
    def tickets_from_space(cls, space_id):
        return cls.query.join(TicketType).filter_by(proposal_space_id=space_id).all()
