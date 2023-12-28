"""Models for syncing tickets to a project from an external ticketing provider."""

from __future__ import annotations

import base64
import os
from collections.abc import Iterable, Sequence
from typing import Any, Self

from coaster.sqlalchemy import LazyRoleSet, with_roles

from . import (
    BaseMixin,
    BaseScopedNameMixin,
    DynamicMapped,
    Mapped,
    Model,
    UuidMixin,
    db,
    relationship,
    sa,
    sa_orm,
)
from .account import Account, AccountEmail
from .email_address import EmailAddress, OptionalEmailAddressMixin
from .project import Project
from .project_membership import project_child_role_map

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


ticket_event_ticket_type = sa.Table(
    'ticket_event_ticket_type',
    Model.metadata,
    sa.Column(
        'ticket_event_id',
        sa.Integer,
        sa.ForeignKey('ticket_event.id'),
        primary_key=True,
    ),
    sa.Column(
        'ticket_type_id', sa.Integer, sa.ForeignKey('ticket_type.id'), primary_key=True
    ),
    sa.Column(
        'created_at',
        sa.TIMESTAMP(timezone=True),
        default=sa.func.utcnow(),
        nullable=False,
    ),
)


class GetTitleMixin(BaseScopedNameMixin):
    @classmethod
    def get(
        cls, parent: Any, name: str | None = None, title: str | None = None
    ) -> Self | None:
        if not bool(name) ^ bool(title):
            raise TypeError("Expects name xor title")
        if name:
            return cls.query.filter_by(parent=parent, name=name).one_or_none()
        return cls.query.filter_by(parent=parent, title=title).one_or_none()

    @classmethod
    def upsert(  # type: ignore[override]  # pylint: disable=arguments-renamed
        cls,
        parent: Any,
        current_name: str | None = None,
        current_title: str | None = None,
        **fields,
    ) -> Self:
        instance = cls.get(parent, current_name, current_title)
        if instance is not None:
            instance._set_fields(fields)  # pylint: disable=protected-access
        else:
            fields.pop('title', None)
            instance = cls(parent=parent, title=current_title, **fields)
            db.session.add(instance)
        return instance


class TicketEvent(GetTitleMixin, Model):
    """
    A discrete event under a project that a ticket grants access to.

    A project may have multiple events, such as a workshop and a two-day conference.
    The workshop is one discrete event, as is each day of the two-day conference.
    Tickets and events have a many-to-many relationship within a project. A ticket type
    may grant access to multiple events and a different ticket type may grant an
    overlapping set of events.
    """

    __tablename__ = 'ticket_event'

    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id'), nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='ticket_events'),
        rw={'project_promoter'},
        grants_via={None: project_child_role_map},
    )
    parent: Mapped[Project] = sa_orm.synonym('project')
    ticket_types: Mapped[list[TicketType]] = with_roles(
        relationship(
            secondary=ticket_event_ticket_type, back_populates='ticket_events'
        ),
        rw={'project_promoter'},
    )
    ticket_participants: DynamicMapped[TicketParticipant] = with_roles(
        relationship(
            secondary='ticket_event_participant',
            lazy='dynamic',
            back_populates='ticket_events',
        ),
        rw={'project_promoter'},
    )
    badge_template: Mapped[str | None] = with_roles(
        sa_orm.mapped_column(sa.Unicode(250), nullable=True), rw={'project_promoter'}
    )

    ticket_event_participants: Mapped[list[TicketEventParticipant]] = relationship(
        back_populates='ticket_event', overlaps='ticket_events,ticket_participants'
    )

    __table_args__ = (
        sa.UniqueConstraint('project_id', 'name'),
        sa.UniqueConstraint('project_id', 'title'),
    )

    __roles__ = {
        'all': {
            'call': {'url_for'},
        },
        'project_promoter': {
            'read': {'name', 'title'},
            'write': {'name', 'title'},
        },
        'project_usher': {
            'read': {'name', 'title'},
        },
    }


class TicketType(GetTitleMixin, Model):
    """
    A ticket type that can grant access to multiple events within a project.

    Eg: Early Geek, Super Early Geek, Workshop A, B, C.
    """

    __tablename__ = 'ticket_type'

    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id'), nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='ticket_types'),
        rw={'project_promoter'},
        grants_via={None: project_child_role_map},
    )
    parent: Mapped[Project] = sa_orm.synonym('project')
    ticket_events: Mapped[list[TicketEvent]] = with_roles(
        relationship(secondary=ticket_event_ticket_type, back_populates='ticket_types'),
        rw={'project_promoter'},
    )

    sync_tickets: Mapped[list[SyncTicket]] = relationship(back_populates='ticket_type')

    __table_args__ = (
        sa.UniqueConstraint('project_id', 'name'),
        sa.UniqueConstraint('project_id', 'title'),
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


class TicketParticipant(OptionalEmailAddressMixin, UuidMixin, BaseMixin, Model):
    """A participant in one or more events, synced from an external ticket source."""

    __tablename__ = 'ticket_participant'
    __email_for__ = 'participant'

    fullname: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=False),
        read={'promoter', 'member', 'scanner'},
    )
    #: Unvalidated phone number
    phone: Mapped[str | None] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=True),
        read={'promoter', 'member', 'scanner'},
    )
    #: Unvalidated Twitter id
    twitter: Mapped[str | None] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=True),
        read={'promoter', 'member', 'scanner'},
    )
    #: Job title
    job_title: Mapped[str | None] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=True),
        read={'promoter', 'member', 'scanner'},
    )
    #: Company
    company: Mapped[str | None] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=True),
        read={'promoter', 'member', 'scanner'},
    )
    #: Participant's city
    city: Mapped[str | None] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=True),
        read={'promoter', 'member', 'scanner'},
    )
    # public key
    puk: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(44), nullable=False, default=make_public_key, unique=True
    )
    key: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(44), nullable=False, default=make_private_key, unique=True
    )
    badge_printed: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, default=False, nullable=False
    )
    participant_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=True
    )
    participant: Mapped[Account | None] = relationship(
        back_populates='ticket_participants'
    )
    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id'), nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(Project, back_populates='ticket_participants'),
        read={'promoter', 'member', 'scanner'},
        grants_via={None: project_child_role_map},
    )

    scanned_contacts: Mapped[ContactExchange] = relationship(
        passive_deletes=True, back_populates='ticket_participant'
    )

    ticket_events: Mapped[list[TicketEvent]] = relationship(
        secondary='ticket_event_participant', back_populates='ticket_participants'
    )
    ticket_event_participants: Mapped[list[TicketEventParticipant]] = relationship(
        overlaps='ticket_events,ticket_participants',
        back_populates='ticket_participant',
    )
    sync_tickets: Mapped[list[SyncTicket]] = relationship(
        back_populates='ticket_participant'
    )

    __table_args__ = (sa.UniqueConstraint('project_id', 'email_address_id'),)

    # Since 'email' comes from the mixin, it's not available to be annotated using
    # `with_roles`. Instead, we have to specify the roles that can access it in here:
    __roles__ = {
        'promoter': {'read': {'email'}},
        'member': {'read': {'email'}},
        'scanner': {'read': {'email'}},
    }

    def roles_for(
        self, actor: Account | None = None, anchors: Sequence = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        if actor is not None:
            if actor == self.participant:
                roles.add('member')
            cx = ContactExchange.query.get((actor.id, self.id))
            if cx is not None:
                roles.add('scanner')
        return roles

    @property
    def avatar(self):
        return self.participant.logo_url if self.participant else ''

    with_roles(avatar, read={'all'})

    @property
    def has_public_profile(self) -> bool:
        return self.participant.has_public_profile if self.participant else False

    with_roles(has_public_profile, read={'all'})

    @property
    def absolute_url(self) -> str | None:
        return self.participant.absolute_url if self.participant else None

    with_roles(absolute_url, read={'all'})

    @classmethod
    def get(
        cls, current_project: Project, current_email: str
    ) -> TicketParticipant | None:
        return cls.query.filter_by(
            project=current_project, email_address=EmailAddress.get(current_email)
        ).one_or_none()

    @classmethod
    def upsert(
        cls, current_project: Project, current_email: str, **fields
    ) -> TicketParticipant:
        ticket_participant = cls.get(current_project, current_email)
        accountemail = AccountEmail.get(current_email)
        if accountemail is not None:
            participant = accountemail.account
        else:
            participant = None
        if ticket_participant is not None:
            ticket_participant.participant = participant
            ticket_participant._set_fields(fields)  # pylint: disable=protected-access
        else:
            with db.session.no_autoflush:
                ticket_participant = cls(
                    project=current_project,
                    participant=participant,
                    email=current_email,
                    **fields,
                )
            db.session.add(ticket_participant)
        return ticket_participant

    def add_events(self, ticket_events: Iterable[TicketEvent]) -> None:
        for ticket_event in ticket_events:
            if ticket_event not in self.ticket_events:
                self.ticket_events.append(ticket_event)

    def remove_events(self, ticket_events: Iterable[TicketEvent]) -> None:
        for ticket_event in ticket_events:
            if ticket_event in self.ticket_events:
                self.ticket_events.remove(ticket_event)

    @classmethod
    def checkin_list(cls, ticket_event: TicketEvent) -> list:  # TODO: List type?
        """
        Return ticket participant details as a comma separated string.

        Also includes associated ticket types.

        FIXME: This is bad design and should be replaced with a saner mechanism.
        """
        query = (
            db.session.query(
                sa.func.distinct(cls.uuid).label('uuid'),
                cls.fullname.label('fullname'),
                EmailAddress.email.label('email'),
                cls.company.label('company'),
                cls.twitter.label('twitter'),
                cls.puk.label('puk'),
                cls.key.label('key'),
                TicketEventParticipant.checked_in.label('checked_in'),
                cls.badge_printed.label('badge_printed'),
                db.session.query(sa.func.string_agg(TicketType.title, ','))
                .select_from(SyncTicket)
                .join(TicketType, SyncTicket.ticket_type_id == TicketType.id)
                .filter(SyncTicket.ticket_participant_id == TicketParticipant.id)
                .label('ticket_type_titles'),
                cls.participant_id.is_not(None).label('has_user'),
            )
            .select_from(TicketParticipant)
            .join(
                TicketEventParticipant,
                TicketParticipant.id == TicketEventParticipant.ticket_participant_id,
            )
            .outerjoin(
                EmailAddress, EmailAddress.id == TicketParticipant.email_address_id
            )
            .outerjoin(
                SyncTicket, TicketParticipant.id == SyncTicket.ticket_participant_id
            )
            .filter(TicketEventParticipant.ticket_event_id == ticket_event.id)
            .order_by(TicketParticipant.fullname)
        )
        return query.all()


class TicketEventParticipant(BaseMixin, Model):
    """Join model between :class:`TicketParticipant` and :class:`TicketEvent`."""

    __tablename__ = 'ticket_event_participant'

    ticket_participant_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('ticket_participant.id'), nullable=False
    )
    ticket_participant: Mapped[TicketParticipant] = relationship(
        back_populates='ticket_event_participants',
        overlaps='ticket_events,ticket_participants',
    )
    ticket_event_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('ticket_event.id'), nullable=False
    )
    ticket_event: Mapped[TicketEvent] = relationship(
        back_populates='ticket_event_participants',
        overlaps='ticket_events,ticket_participants',
    )
    checked_in: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, default=False, nullable=False
    )

    __table_args__ = (
        # Uses a custom name that is not as per convention because the default name is
        # too long for PostgreSQL
        sa.UniqueConstraint(
            'ticket_event_id',
            'ticket_participant_id',
            name='ticket_event_participant_event_id_participant_id_key',
        ),
    )

    @classmethod
    def get(
        cls, ticket_event: TicketEvent, participant_uuid_b58: str
    ) -> TicketEventParticipant | None:
        return (
            cls.query.join(TicketParticipant)
            .filter(
                TicketEventParticipant.ticket_event == ticket_event,
                TicketParticipant.uuid_b58 == participant_uuid_b58,
            )
            .one_or_none()
        )


class TicketClient(BaseMixin, Model):
    __tablename__ = 'ticket_client'
    name: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    client_eventid: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    clientid: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    client_secret: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    client_access_token: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(80), nullable=False), rw={'project_promoter'}
    )
    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id'), nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='ticket_clients'),
        rw={'project_promoter'},
        grants_via={None: project_child_role_map},
    )

    sync_tickets: Mapped[list[SyncTicket]] = relationship(
        back_populates='ticket_client'
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


class SyncTicket(BaseMixin, Model):
    """Model for a ticket that was bought elsewhere, like Boxoffice or Explara."""

    __tablename__ = 'sync_ticket'

    ticket_no: Mapped[str] = sa_orm.mapped_column(sa.Unicode(80), nullable=False)
    order_no: Mapped[str] = sa_orm.mapped_column(sa.Unicode(80), nullable=False)
    ticket_type_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('ticket_type.id'), nullable=False
    )
    ticket_type: Mapped[TicketType] = relationship(back_populates='sync_tickets')
    ticket_participant_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('ticket_participant.id'), nullable=False
    )
    ticket_participant: Mapped[TicketParticipant] = relationship(
        back_populates='sync_tickets'
    )
    ticket_client_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('ticket_client.id'), nullable=False
    )
    ticket_client: Mapped[TicketClient] = relationship(back_populates='sync_tickets')
    __table_args__ = (sa.UniqueConstraint('ticket_client_id', 'order_no', 'ticket_no'),)

    @classmethod
    def get(
        cls, ticket_client: TicketClient, order_no: str, ticket_no: str
    ) -> SyncTicket | None:
        return cls.query.filter_by(
            ticket_client=ticket_client, order_no=order_no, ticket_no=ticket_no
        ).one_or_none()

    @classmethod
    def upsert(
        cls, ticket_client: TicketClient, order_no: str, ticket_no: str, **fields
    ) -> SyncTicket:
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
            ticket = cls(
                ticket_client=ticket_client,
                order_no=order_no,
                ticket_no=ticket_no,
                **fields,
            )

            db.session.add(ticket)

        return ticket


# Tail imports
from .contact_exchange import ContactExchange
