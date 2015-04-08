# -*- coding: utf-8 -*-
from . import db, BaseMixin
from .space import ProposalSpace
from .user import User
import uuid
from .. import app
import qrcode
import qrcode.image.svg
from flask import url_for, render_template


__all__ = ['Event', 'TicketType', 'EventTicketType', 'Participant', 'Attendee', 'SyncTicket']


def make_key():
    # 8-character string sliced from uuid
    return str(uuid.uuid4())[0:8]


def split_name(fullname):
    name_splits = fullname.split()
    first_name = name_splits[0]
    last_name = " ".join([s for s in name_splits[1:]])
    return first_name, last_name


def format_twitter(twitter):
    return "@{0}".format(twitter)


def make_qrcode(data, path):
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(data, image_factory=factory)
    img.save(path)
    return path


class EventTicketType(BaseMixin, db.Model):
    __tablename__ = 'event_ticket_type'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False, primary_key=True)
    ticket_type_id = db.Column(None, db.ForeignKey('ticket_type.id'), nullable=False, primary_key=True)


class Event(BaseMixin, db.Model):
    __tablename__ = 'event'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.Unicode(80), nullable=True)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('events', cascade='all, delete-orphan', lazy='dynamic'))
    ticket_types = db.relationship("TicketType", secondary=EventTicketType.__tablename__)


class TicketType(BaseMixin, db.Model):
    __tablename__ = 'ticket_type'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.Unicode(80), nullable=True)
    proposal_space_id = db.Column(None, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('ticket_types', cascade='all, delete-orphan', lazy='dynamic'))
    events = db.relationship("Event", secondary=EventTicketType.__tablename__)


class Participant(BaseMixin, db.Model):
    __tablename__ = 'participant'

    fullname = db.Column(db.Unicode(80), nullable=True)
    #: Unvalidated email address
    email = db.Column(db.Unicode(80), nullable=True, unique=True)
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
    #: Access key for connecting to the user record (nulled when linked)
    key = db.Column(db.Unicode(44), nullable=True, default=make_key, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('participant', cascade="all, delete-orphan"))
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=True)
    proposal_space = db.relationship(ProposalSpace,
        backref=db.backref('participants', cascade='all, delete-orphan', lazy='dynamic'))

    def make_file_path(self, space):
        return "{0}_{1}_{2}".format(space.profile.name, space.name, str(self.id))

    def make_badge(self, space, qrcode_full_path=True):
        first_name, last_name = split_name(self.fullname)
        qrcode_filename = '{0}.{1}'.format(self.make_file_path(space), 'svg')
        qrcode_data = "{0}:{1}".format(str(self.id), self.key)
        qrcode_path = "{0}/{1}".format(app.config.get('BADGES_PATH'), qrcode_filename)
        make_qrcode(qrcode_data, qrcode_path)
        if qrcode_full_path:
            qrcode_url = url_for('static', filename="{0}/{1}".format('badges', qrcode_filename))
        else:
            qrcode_url = qrcode_filename
        qrcode_content = open(qrcode_path).read()
        badge_html = render_template('badge.html', first_name=first_name, last_name=last_name, twitter=format_twitter(self.twitter), qrcode_path=qrcode_url, qrcode_content=qrcode_content, participant=self)
        return badge_html

    def make_badge_file(self, space):
        basepath = app.config['BADGES_PATH']
        filename = '{0}.{1}'.format(self.make_file_path(space), 'html')
        path = "{0}/{1}".format(basepath, filename)
        html = self.make_badge(space, qrcode_full_path=False)
        f = open(path, "wb")
        f.write(html)
        f.close()


class Attendee(BaseMixin, db.Model):
    __tablename__ = 'attendee'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False, primary_key=True)
    participant = db.relationship(Participant,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False, primary_key=True)
    event = db.relationship(Event,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    checked_in = db.Column(db.Boolean, default=False, nullable=True)


class SyncTicket(BaseMixin, db.Model):
    __tablename__ = 'sync_ticket'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    ticket_no = db.Column(db.Unicode(80), nullable=True, unique=True)
    order_no = db.Column(db.Unicode(80), nullable=True)
    ticket_type_id = db.Column(None, db.ForeignKey('ticket_type.id'), nullable=False, primary_key=True)
    ticket_type = db.relationship(TicketType,
        backref=db.backref('sync_tickets', cascade='all, delete-orphan', lazy='dynamic'))
    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False, primary_key=True)
    participant = db.relationship(Participant, primaryjoin=participant_id == Participant.id,
        backref=db.backref('sync_tickets', cascade="all, delete-orphan"))

    @classmethod
    def tickets_from_space(cls, space_id):
        return cls.query.join(TicketType).filter_by(proposal_space_id=space_id).all()
