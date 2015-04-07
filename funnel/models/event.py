# -*- coding: utf-8 -*-
from . import db, BaseMixin
from .space import ProposalSpace
from .user import User
import uuid
import svgutils.transform as sg
import sys
import qrcode
import qrcode.image.svg
import subprocess
import os
import time
from .. import app

__all__ = ['Event', 'TicketType', 'EventTicketType', 'Participant', 'Attendee', 'SyncTicket']


def make_key():
    # 8-character string sliced from uuid
    return str(uuid.uuid4())[0:8]


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

    def make_badge(self, space):
        participant = self
        basepath = app.config['BADGES_PATH']
        filename = '{0}_{1}_{2}'.format(space.profile.name, space.name, str(self.id))
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make("{0}:{1}".format(str(participant.id), participant.key), image_factory=factory)
        img_path = "{0}/{1}.svg".format(basepath, filename)
        img.save(img_path)

        fields = []
        name_splits = participant.fullname.split()
        first_name = name_splits[0]
        last_name = "".join([s for s in name_splits[1:]])
        x = 400
        y = 300
        fields.append(sg.TextElement(x, y, first_name, size=140, weight="bold"))
        if last_name:
            y += 100
            fields.append(sg.TextElement(x, y, last_name, size=80))
        if participant.company:
            y += 100
            fields.append(sg.TextElement(x, y, participant.company, size=60))
        if participant.twitter:
            y += 100
            fields.append(sg.TextElement(x, y, "@{0}".format(participant.twitter), size=60))
        y += 50
        qr_sg = sg.fromfile(img_path).getroot()
        qr_sg.moveto(370, 650, scale=15)
        fields.append(qr_sg)

        # badge_sg = sg.fromfile(badge_template)
        badge_sg = sg.SVGFigure("50cm", "30cm")
        badge_sg.append(fields)
        # badge_path = 'badge_svgs/{0}_{1}.svg'.format(filename, 'badge')
        badge_svg_path = "{0}/{1}_badge.svg".format(basepath, filename)
        badge_sg.save(badge_svg_path)
        badge_path = '{0}/{1}.pdf'.format(basepath, filename)
        # inkscape --export-pdf=metarefresh_2015_1.svg_badge.pdf metarefresh_2015_1.svg_badge.svg
        subprocess.call(['inkscape', '--export-pdf={0}'.format(badge_path), badge_svg_path])
        return badge_path

    def print_badge(self, space):
        path = app.config['BADGES_PATH'] + '/{0}'.format(self.badge_url(space))
        os.system("lpr -o page-ranges=1 -P %s %s" % (app.config['PRINTER_NAME'], path))

    def badge_url(self, space):
        path = '{0}_{1}_{2}.pdf'.format(space.profile.name, space.name, str(self.id))
        return path


class Attendee(BaseMixin, db.Model):
    __tablename__ = 'attendee'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    participant_id = db.Column(None, db.ForeignKey('participant.id'), nullable=False, primary_key=True)
    participant = db.relationship(Participant,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))
    event_id = db.Column(None, db.ForeignKey('event.id'), nullable=False, primary_key=True)
    event = db.relationship(Event,
        backref=db.backref('attendees', cascade='all, delete-orphan', lazy='dynamic'))


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
