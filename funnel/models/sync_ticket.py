import base64
import os

from . import BaseMixin, BaseScopedNameMixin, UuidMixin, db, with_roles
from .email_address import EmailAddress, EmailAddressMixin
from .project import Project
from .project_membership import project_child_role_map
from .user import User, UserEmail

__all__ = [
    'SyncTicket',
    'TicketClient',
    'TicketEvent',
    'TicketEventParticipant',
    'TicketParticipant',
    'TicketType',
]


def make_key():
    return base64.urlsafe_b64encode(os.urandom(128)).decode('utf-8')


def make_public_key():
    return make_key()[:8]


def make_private_key():
    return make_key()[:8]


ticket_event_ticket_type = db.Table(
    'ticket_event_ticket_type',
    db.Model.metadata,
    db.Column(
        'ticket_event_id', None, db.ForeignKey('ticket_event.id'), primary_key=True
    ),
    db.Column(
        'ticket_type_id', None, db.ForeignKey('ticket_type.id'), primary_key=True
    ),
    db.Column(
        'created_at',
        db.TIMESTAMP(timezone=True),
        default=db.func.utcnow(),
        nullable=False,
    ),
)


class GetTitleMixin(BaseScopedNameMixin):
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


class TicketEvent(GetTitleMixin, db.Model):
    """
    A discrete event under a project that a ticket grants access to.

    A project may have multiple events, such as a workshop and a two-day conference.
    The workshop is one discrete event, as is each day of the two-day conference.
    Tickets and events have a many-to-many relationship within a project. A ticket type
    may grant access to multiple events and a different ticket type may grant an
    overlapping set of events.
    """

    __tablename__ = 'ticket_event'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(Project, backref=db.backref('events', cascade='all')),
        grants_via={None: project_child_role_map},
    )
    parent = db.synonym('project')
    ticket_types = db.relationship(
        'TicketType', secondary=ticket_event_ticket_type, back_populates='events'
    )
    participants = db.relationship(
        'TicketParticipant',
        secondary='ticket_event_participant',
        backref='events',
        lazy='dynamic',
    )
    badge_template = db.Column(db.Unicode(250), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'name'),
        db.UniqueConstraint('project_id', 'title'),
    )


class TicketType(GetTitleMixin, db.Model):
    """
    Models different types of tickets. Eg: Early Geek, Super Early Geek, Workshop A.
    A ticket type is associated with multiple events.
    """

    __tablename__ = 'ticket_type'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(Project, backref=db.backref('ticket_types', cascade='all')),
        grants_via={None: project_child_role_map},
    )
    parent = db.synonym('project')
    events = db.relationship(
        TicketEvent, secondary=ticket_event_ticket_type, back_populates='ticket_types'
    )

    __table_args__ = (
        db.UniqueConstraint('project_id', 'name'),
        db.UniqueConstraint('project_id', 'title'),
    )


class TicketParticipant(EmailAddressMixin, UuidMixin, BaseMixin, db.Model):
    """
    Model users participating in one or multiple events.
    """

    __tablename__ = 'ticket_participant'
    __email_optional__ = False
    __email_for__ = 'user'

    fullname = with_roles(
        db.Column(db.Unicode(80), nullable=False),
        read={'concierge', 'subject', 'scanner'},
    )
    #: Unvalidated phone number
    phone = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'},
    )
    #: Unvalidated Twitter id
    twitter = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'},
    )
    #: Job title
    job_title = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'},
    )
    #: Company
    company = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'},
    )
    #: Participant's city
    city = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'concierge', 'subject', 'scanner'},
    )
    # public key
    puk = db.Column(
        db.Unicode(44), nullable=False, default=make_public_key, unique=True
    )
    key = db.Column(
        db.Unicode(44), nullable=False, default=make_private_key, unique=True
    )
    badge_printed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, backref=db.backref('participants', cascade='all'))
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(
            Project, backref=db.backref('participants', lazy='dynamic', cascade='all')
        ),
        read={'concierge', 'subject', 'scanner'},
        grants_via={None: project_child_role_map},
    )

    __table_args__ = (db.UniqueConstraint('project_id', 'email_address_id'),)

    # Since 'email' comes from the mixin, it's not available to be annotated using
    # `with_roles`. Instead, we have to specify the roles that can access it in here:
    __roles__ = {
        'concierge': {'read': {'email'}},
        'subject': {'read': {'email'}},
        'scanner': {'read': {'email'}},
    }

    def roles_for(self, actor, anchors=()):
        roles = super(TicketParticipant, self).roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('subject')
        cx = ContactExchange.query.get((actor.id, self.id))
        if cx is not None:
            roles.add('scanner')
        return roles

    def permissions(self, user, inherited=None):
        perms = super(TicketParticipant, self).permissions(user, inherited)
        if self.project is not None:
            return self.project.permissions(user) | perms
        return perms

    @with_roles(read={'all'})
    @property
    def avatar(self):
        return self.user.avatar if self.user else ''

    @with_roles(read={'all'})
    @property
    def has_public_profile(self):
        return self.user.has_public_profile if self.user else False

    @with_roles(read={'all'})
    @property
    def profile_url(self):
        return (
            self.user.profile.url_for()
            if self.user and self.user.has_public_profile
            else None
        )

    @classmethod
    def get(cls, current_project, current_email):
        return cls.query.filter_by(
            project=current_project, email_address=EmailAddress.get(current_email)
        ).one_or_none()

    @classmethod
    def upsert(cls, current_project, current_email, **fields):
        participant = cls.get(current_project, current_email)
        useremail = UserEmail.get(current_email)
        if useremail:
            user = useremail.user
        else:
            user = None
        if participant:
            participant.user = user
            participant._set_fields(fields)
        else:
            with db.session.no_autoflush:
                participant = cls(
                    project=current_project, user=user, email=current_email, **fields
                )
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
    def checkin_list(cls, ticket_event):
        """
        Returns participant details along with their associated ticket types as a
        comma-separated string.
        """
        # FIXME: Replace with SQLAlchemy objects
        participant_list = (
            db.session.query(
                'uuid',
                'fullname',
                'email',
                'company',
                'twitter',
                'puk',
                'key',
                'checked_in',
                'badge_printed',
                'ticket_type_titles',
            )
            .from_statement(
                db.text(
                    '''
                    SELECT distinct(ticket_participant.uuid), ticket_participant.fullname, email_address.email, ticket_participant.company, ticket_participant.twitter, ticket_participant.puk, ticket_participant.key, ticket_event_participant.checked_in, ticket_participant.badge_printed,
                    (SELECT string_agg(title, ',') FROM sync_ticket INNER JOIN ticket_type ON sync_ticket.ticket_type_id = ticket_type.id where sync_ticket.ticket_participant_id = ticket_participant.id) AS ticket_type_titles
                    FROM ticket_participant INNER JOIN ticket_event_participant ON ticket_participant.id = ticket_event_participant.ticket_participant_id INNER JOIN email_address ON email_address.id = ticket_participant.email_address_id LEFT OUTER JOIN sync_ticket ON ticket_participant.id = sync_ticket.ticket_participant_id
                    WHERE ticket_event_participant.ticket_event_id = :ticket_event_id
                    ORDER BY ticket_participant.fullname
                    '''
                )
            )
            .params(ticket_event_id=ticket_event.id)
            .all()
        )
        return participant_list


class TicketEventParticipant(BaseMixin, db.Model):
    """
    Join model between Participant and Event.
    """

    __tablename__ = 'ticket_event_participant'

    ticket_participant_id = db.Column(
        None, db.ForeignKey('ticket_participant.id'), nullable=False
    )
    participant = db.relationship(
        TicketParticipant, backref=db.backref('attendees', cascade='all')
    )
    ticket_event_id = db.Column(None, db.ForeignKey('ticket_event.id'), nullable=False)
    event = db.relationship(TicketEvent, backref=db.backref('attendees', cascade='all'))
    checked_in = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        # Uses a custom name that is not as per convention because the default name is
        # too long for PostgreSQL
        db.UniqueConstraint(
            'ticket_event_id',
            'ticket_participant_id',
            name='ticket_event_participant_event_id_participant_id_key',
        ),
    )

    @classmethod
    def get(cls, event, participant_uuid_b58):
        return (
            cls.query.join(TicketParticipant)
            .filter(
                TicketEventParticipant.event == event,
                TicketParticipant.uuid_b58 == participant_uuid_b58,
            )
            .one_or_none()
        )


class TicketClient(BaseMixin, db.Model):
    __tablename__ = 'ticket_client'
    name = db.Column(db.Unicode(80), nullable=False)
    client_eventid = db.Column(db.Unicode(80), nullable=False)
    clientid = db.Column(db.Unicode(80), nullable=False)
    client_secret = db.Column(db.Unicode(80), nullable=False)
    client_access_token = db.Column(db.Unicode(80), nullable=False)
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(Project, backref=db.backref('ticket_clients', cascade='all')),
        grants_via={None: project_child_role_map},
    )

    def import_from_list(self, ticket_list):
        """
        Batch upserts the tickets and its associated ticket types and participants.
        Cancels the tickets in cancel_list.
        """
        for ticket_dict in ticket_list:
            ticket_type = TicketType.upsert(
                self.project, current_title=ticket_dict['ticket_type']
            )

            participant = TicketParticipant.upsert(
                self.project,
                ticket_dict['email'],
                fullname=ticket_dict['fullname'],
                phone=ticket_dict['phone'],
                twitter=ticket_dict['twitter'],
                company=ticket_dict['company'],
                job_title=ticket_dict['job_title'],
                city=ticket_dict['city'],
            )

            ticket = SyncTicket.get(
                self, ticket_dict.get('order_no'), ticket_dict.get('ticket_no')
            )
            if ticket and (
                ticket.participant is not participant
                or ticket_dict.get('status') == 'cancelled'
            ):
                # Ensure that the participant of a transferred or cancelled ticket does
                # not have access to this ticket's events
                ticket.participant.remove_events(ticket_type.events)

            if ticket_dict.get('status') == 'confirmed':
                ticket = SyncTicket.upsert(
                    self,
                    ticket_dict.get('order_no'),
                    ticket_dict.get('ticket_no'),
                    participant=participant,
                    ticket_type=ticket_type,
                )
                # Ensure that the new or updated participant has access to events
                ticket.participant.add_events(ticket_type.events)

    def permissions(self, user, inherited=None):
        perms = super(TicketClient, self).permissions(user, inherited)
        if self.project is not None:
            return self.project.permissions(user) | perms
        return perms


class SyncTicket(BaseMixin, db.Model):
    """ Model for a ticket that was bought elsewhere, like Boxoffice or Explara."""

    __tablename__ = 'sync_ticket'

    ticket_no = db.Column(db.Unicode(80), nullable=False)
    order_no = db.Column(db.Unicode(80), nullable=False)
    ticket_type_id = db.Column(None, db.ForeignKey('ticket_type.id'), nullable=False)
    ticket_type = db.relationship(
        TicketType, backref=db.backref('sync_tickets', cascade='all')
    )
    ticket_participant_id = db.Column(
        None, db.ForeignKey('ticket_participant.id'), nullable=False
    )
    participant = db.relationship(
        TicketParticipant,
        backref=db.backref('sync_tickets', cascade='all'),
    )
    ticket_client_id = db.Column(
        None, db.ForeignKey('ticket_client.id'), nullable=False
    )
    ticket_client = db.relationship(
        TicketClient, backref=db.backref('sync_tickets', cascade='all')
    )
    __table_args__ = (db.UniqueConstraint('ticket_client_id', 'order_no', 'ticket_no'),)

    @classmethod
    def get(cls, ticket_client, order_no, ticket_no):
        return cls.query.filter_by(
            ticket_client=ticket_client, order_no=order_no, ticket_no=ticket_no
        ).one_or_none()

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
            ticket = SyncTicket(
                ticket_client=ticket_client,
                order_no=order_no,
                ticket_no=ticket_no,
                **fields,
            )

            db.session.add(ticket)

        return ticket


# Tail imports to avoid cyclic dependency errors, for symbols used only in methods
from .contact_exchange import ContactExchange  # isort:skip
