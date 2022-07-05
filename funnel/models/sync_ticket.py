"""Models for syncing tickets to a project from an external ticketing provider."""

from __future__ import annotations

from typing import Iterable, Optional, Set
import base64
import os

from . import BaseMixin, BaseScopedNameMixin, UuidMixin, db, with_roles
from .email_address import EmailAddress, EmailAddressMixin
from .helpers import reopen
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
    def get(cls, parent, name=None, title=None):
        if not bool(name) ^ bool(title):
            raise TypeError("Expects name xor title")
        if name:
            return cls.query.filter_by(parent=parent, name=name).one_or_none()
        return cls.query.filter_by(parent=parent, title=title).one_or_none()

    @classmethod
    def upsert(  # pylint: disable=arguments-renamed
        cls, parent, current_name=None, current_title=None, **fields
    ):
        instance = cls.get(parent, current_name, current_title)
        if instance is not None:
            instance._set_fields(fields)  # pylint: disable=protected-access
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
        db.relationship(Project, backref=db.backref('ticket_events', cascade='all')),
        rw={'project_promoter'},
        grants_via={None: project_child_role_map},
    )
    parent = db.synonym('project')
    ticket_types = with_roles(
        db.relationship(
            'TicketType',
            secondary=ticket_event_ticket_type,
            back_populates='ticket_events',
        ),
        rw={'project_promoter'},
    )
    ticket_participants = with_roles(
        db.relationship(
            'TicketParticipant',
            secondary='ticket_event_participant',
            backref='ticket_events',
            lazy='dynamic',
        ),
        rw={'project_promoter'},
    )
    badge_template = with_roles(
        db.Column(db.Unicode(250), nullable=True), rw={'project_promoter'}
    )

    __table_args__ = (
        db.UniqueConstraint('project_id', 'name'),
        db.UniqueConstraint('project_id', 'title'),
    )

    __roles__ = {
        'all': {
            'call': {'url_for'},
        },
        'project_promoter': {
            'read': {'name', 'title'},
            'write': {'name', 'title'},
        },
    }


class TicketType(GetTitleMixin, db.Model):
    """
    A ticket type that can grant access to multiple events within a project.

    Eg: Early Geek, Super Early Geek, Workshop A, B, C.
    """

    __tablename__ = 'ticket_type'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(Project, backref=db.backref('ticket_types', cascade='all')),
        rw={'project_promoter'},
        grants_via={None: project_child_role_map},
    )
    parent = db.synonym('project')
    ticket_events = with_roles(
        db.relationship(
            TicketEvent,
            secondary=ticket_event_ticket_type,
            back_populates='ticket_types',
        ),
        rw={'project_promoter'},
    )

    __table_args__ = (
        db.UniqueConstraint('project_id', 'name'),
        db.UniqueConstraint('project_id', 'title'),
    )

    __roles__ = {
        'all': {
            'call': {'url_for'},
        },
        'project_promoter': {
            'read': {'name', 'title'},
            'write': {'name', 'title'},
        },
    }


class TicketParticipant(EmailAddressMixin, UuidMixin, BaseMixin, db.Model):
    """A participant in one or more events, synced from an external ticket source."""

    __tablename__ = 'ticket_participant'
    __email_optional__ = False
    __email_for__ = 'user'

    fullname = with_roles(
        db.Column(db.Unicode(80), nullable=False),
        read={'promoter', 'subject', 'scanner'},
    )
    #: Unvalidated phone number
    phone = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'promoter', 'subject', 'scanner'},
    )
    #: Unvalidated Twitter id
    twitter = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'promoter', 'subject', 'scanner'},
    )
    #: Job title
    job_title = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'promoter', 'subject', 'scanner'},
    )
    #: Company
    company = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'promoter', 'subject', 'scanner'},
    )
    #: Participant's city
    city = with_roles(
        db.Column(db.Unicode(80), nullable=True),
        read={'promoter', 'subject', 'scanner'},
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
    user = db.relationship(
        User, backref=db.backref('ticket_participants', cascade='all')
    )
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(Project, back_populates='ticket_participants'),
        read={'promoter', 'subject', 'scanner'},
        grants_via={None: project_child_role_map},
    )

    __table_args__ = (db.UniqueConstraint('project_id', 'email_address_id'),)

    # Since 'email' comes from the mixin, it's not available to be annotated using
    # `with_roles`. Instead, we have to specify the roles that can access it in here:
    __roles__ = {
        'promoter': {'read': {'email'}},
        'subject': {'read': {'email'}},
        'scanner': {'read': {'email'}},
    }

    def roles_for(self, actor: Optional[User] = None, anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        if actor is not None:
            if actor == self.user:
                roles.add('subject')
            cx = ContactExchange.query.get((actor.id, self.id))
            if cx is not None:
                roles.add('scanner')
        return roles

    @property
    def avatar(self):
        return self.user.avatar if self.user else ''

    with_roles(avatar, read={'all'})

    @property
    def has_public_profile(self):
        return self.user.has_public_profile if self.user else False

    with_roles(has_public_profile, read={'all'})

    @property
    def profile_url(self):
        return (
            self.user.profile.url_for()
            if self.user and self.user.has_public_profile
            else None
        )

    with_roles(profile_url, read={'all'})

    @classmethod
    def get(cls, current_project, current_email):
        return cls.query.filter_by(
            project=current_project, email_address=EmailAddress.get(current_email)
        ).one_or_none()

    @classmethod
    def upsert(cls, current_project, current_email, **fields):
        ticket_participant = cls.get(current_project, current_email)
        useremail = UserEmail.get(current_email)
        if useremail is not None:
            user = useremail.user
        else:
            user = None
        if ticket_participant is not None:
            ticket_participant.user = user
            ticket_participant._set_fields(fields)  # pylint: disable=protected-access
        else:
            with db.session.no_autoflush:
                ticket_participant = cls(
                    project=current_project, user=user, email=current_email, **fields
                )
            db.session.add(ticket_participant)
        return ticket_participant

    def add_events(self, ticket_events):
        for ticket_event in ticket_events:
            if ticket_event not in self.ticket_events:
                self.ticket_events.append(ticket_event)

    def remove_events(self, ticket_events):
        for ticket_event in ticket_events:
            if ticket_event in self.ticket_events:
                self.ticket_events.remove(ticket_event)

    @classmethod
    def checkin_list(cls, ticket_event):
        """
        Return ticket participant details as a comma separated string.

        Also includes associated ticket types.

        FIXME: This is bad design and should be replaced with a saner mechanism.
        """
        query = (
            db.session.query(
                db.func.distinct(cls.uuid).label('uuid'),
                cls.fullname.label('fullname'),
                EmailAddress.email.label('email'),
                cls.company.label('company'),
                cls.twitter.label('twitter'),
                cls.puk.label('puk'),
                cls.key.label('key'),
                TicketEventParticipant.checked_in.label('checked_in'),
                cls.badge_printed.label('badge_printed'),
                db.session.query(db.func.string_agg(TicketType.title, ','))
                .select_from(SyncTicket)
                .join(TicketType, SyncTicket.ticket_type_id == TicketType.id)
                .filter(SyncTicket.ticket_participant_id == TicketParticipant.id)
                .label('ticket_type_titles'),
                cls.user_id.isnot(None).label('has_user'),
            )
            .select_from(TicketParticipant)
            .join(
                TicketEventParticipant,
                TicketParticipant.id == TicketEventParticipant.ticket_participant_id,
            )
            .join(EmailAddress, EmailAddress.id == TicketParticipant.email_address_id)
            .outerjoin(
                SyncTicket, TicketParticipant.id == SyncTicket.ticket_participant_id
            )
            .filter(TicketEventParticipant.ticket_event_id == ticket_event.id)
            .order_by(TicketParticipant.fullname)
        )
        return query.all()


class TicketEventParticipant(BaseMixin, db.Model):
    """Join model between :class:`TicketParticipant` and :class:`TicketEvent`."""

    __tablename__ = 'ticket_event_participant'

    ticket_participant_id = db.Column(
        None, db.ForeignKey('ticket_participant.id'), nullable=False
    )
    ticket_participant = db.relationship(
        TicketParticipant,
        backref=db.backref(
            'ticket_event_participants',
            cascade='all',
            overlaps='ticket_events,ticket_participants',
        ),
        overlaps='ticket_events,ticket_participants',
    )
    ticket_event_id = db.Column(None, db.ForeignKey('ticket_event.id'), nullable=False)
    ticket_event = db.relationship(
        TicketEvent,
        backref=db.backref(
            'ticket_event_participants',
            cascade='all',
            overlaps='ticket_events,ticket_participants',
        ),
        overlaps='ticket_events,ticket_participants',
    )
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
    def get(cls, ticket_event, participant_uuid_b58):
        return (
            cls.query.join(TicketParticipant)
            .filter(
                TicketEventParticipant.ticket_event == ticket_event,
                TicketParticipant.uuid_b58 == participant_uuid_b58,
            )
            .one_or_none()
        )


class TicketClient(BaseMixin, db.Model):
    __tablename__ = 'ticket_client'
    name = with_roles(
        db.Column(db.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    client_eventid = with_roles(
        db.Column(db.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    clientid = with_roles(
        db.Column(db.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    client_secret = with_roles(
        db.Column(db.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    client_access_token = with_roles(
        db.Column(db.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(Project, backref=db.backref('ticket_clients', cascade='all')),
        rw={'project_promoter'},
        grants_via={None: project_child_role_map},
    )

    __roles__ = {'all': {'call': {'url_for'}}}

    def import_from_list(self, ticket_list):
        """Batch upsert tickets and their associated ticket types and participants."""
        for ticket_dict in ticket_list:
            ticket_type = TicketType.upsert(
                self.project, current_title=ticket_dict['ticket_type']
            )

            ticket_participant = TicketParticipant.upsert(
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
                ticket.ticket_participant != ticket_participant
                or ticket_dict.get('status') == 'cancelled'
            ):
                # Ensure that the participant of a transferred or cancelled ticket does
                # not have access to this ticket's events
                ticket.ticket_participant.remove_events(ticket_type.ticket_events)

            if ticket_dict.get('status') == 'confirmed':
                ticket = SyncTicket.upsert(
                    self,
                    ticket_dict.get('order_no'),
                    ticket_dict.get('ticket_no'),
                    ticket_participant=ticket_participant,
                    ticket_type=ticket_type,
                )
                # Ensure that the new or updated participant has access to events
                ticket.ticket_participant.add_events(ticket_type.ticket_events)


class SyncTicket(BaseMixin, db.Model):
    """Model for a ticket that was bought elsewhere, like Boxoffice or Explara."""

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
    ticket_participant = db.relationship(
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
        Update or insert ticket details.

        Returns a tuple containing the upserted ticket, and the participant the ticket
        was previously associated with or None if there was no earlier participant.
        """
        ticket = cls.get(ticket_client, order_no, ticket_no)
        if ticket is not None:
            ticket._set_fields(fields)  # pylint: disable=protected-access
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


@reopen(Project)
class __Project:
    # XXX: This relationship exposes an edge case in RoleMixin. It previously expected
    # TicketParticipant.user to be unique per project, meaning one user could have one
    # participant ticket only. This is not guaranteed by the model as tickets are unique
    # per email address per ticket type, and one user can have (a) two email addresses
    # with tickets, or (b) tickets of different types. RoleMixin has since been patched
    # to look for the first matching record (.first() instead of .one()). This may
    # expose a new edge case in future in case the TicketParticipant model adds an
    # `offered_roles` method, as only the first matching record's method will be called
    ticket_participants = with_roles(
        db.relationship(
            TicketParticipant, lazy='dynamic', cascade='all', back_populates='project'
        ),
        grants_via={'user': {'participant'}},
    )


# Tail imports to avoid cyclic dependency errors, for symbols used only in methods
# pylint: disable=wrong-import-position
from .contact_exchange import ContactExchange  # isort:skip
