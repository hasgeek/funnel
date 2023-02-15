"""Model for contacts scanned from badges at in-person events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from itertools import groupby
from typing import Collection, Iterable, Optional
from uuid import UUID

from sqlalchemy.ext.associationproxy import association_proxy

from pytz import timezone

from coaster.sqlalchemy import LazyRoleSet
from coaster.utils import uuid_to_base58

from ..typing import OptionalMigratedTables
from . import Mapped, RoleMixin, TimestampMixin, db, sa
from .project import Project
from .sync_ticket import TicketParticipant
from .user import User

__all__ = ['ContactExchange']


# Data classes for returning contacts grouped by project and date
@dataclass
class ProjectId:
    """Holder for minimal :class:`~funnel.models.project.Project` information."""

    id: int  # noqa: A003
    uuid: UUID
    uuid_b58: str
    title: str
    timezone: str


@dataclass
class DateCountContacts:
    """Contacts per date of a Project's schedule."""

    date: datetime
    count: int
    contacts: Collection[ContactExchange]


class ContactExchange(
    TimestampMixin,
    RoleMixin,
    db.Model,  # type: ignore[name-defined]
):
    """Model to track who scanned whose badge, in which project."""

    __tablename__ = 'contact_exchange'
    __allow_unmapped__ = True
    #: User who scanned this contact
    user_id = sa.Column(
        sa.Integer, sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True
    )
    user: Mapped[User] = sa.orm.relationship(
        User,
        backref=sa.orm.backref(
            'scanned_contacts',
            lazy='dynamic',
            order_by='ContactExchange.scanned_at.desc()',
            passive_deletes=True,
        ),
    )
    #: Participant whose contact was scanned
    ticket_participant_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('ticket_participant.id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
    )
    ticket_participant: Mapped[TicketParticipant] = sa.orm.relationship(
        TicketParticipant,
        backref=sa.orm.backref('scanned_contacts', passive_deletes=True),
    )
    #: Datetime at which the scan happened
    scanned_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )
    #: Note recorded by the user (plain text)
    description = sa.Column(sa.UnicodeText, nullable=False, default='')
    #: Archived flag
    archived = sa.Column(sa.Boolean, nullable=False, default=False)

    __roles__ = {
        'owner': {
            'read': {
                'user',
                'ticket_participant',
                'scanned_at',
                'description',
                'archived',
            },
            'write': {'description', 'archived'},
        },
        'subject': {'read': {'user', 'ticket_participant', 'scanned_at'}},
    }

    def roles_for(
        self, actor: Optional[User] = None, anchors: Iterable = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        if actor is not None:
            if actor == self.user:
                roles.add('owner')
            if actor == self.ticket_participant.user:
                roles.add('subject')
        return roles

    @classmethod
    def migrate_user(  # type: ignore[return]
        cls, old_user: User, new_user: User
    ) -> OptionalMigratedTables:
        """Migrate one user account to another when merging user accounts."""
        ticket_participant_ids = {
            ce.ticket_participant_id for ce in new_user.scanned_contacts
        }
        for ce in old_user.scanned_contacts:
            if ce.ticket_participant_id not in ticket_participant_ids:
                ce.user = new_user
            else:
                # Discard duplicate contact exchange
                db.session.delete(ce)

    @classmethod
    def grouped_counts_for(cls, user, archived=False):
        """Return count of contacts grouped by project and date."""
        subq = sa.select(
            cls.scanned_at.label('scanned_at'),
            Project.id.label('project_id'),
            Project.uuid.label('project_uuid'),
            Project.timezone.label('project_timezone'),
            Project.title.label('project_title'),
        ).filter(
            cls.ticket_participant_id == TicketParticipant.id,
            TicketParticipant.project_id == Project.id,
            cls.user == user,
        )

        if not archived:
            # If archived: return everything (contacts including archived contacts)
            # If not archived: return only unarchived contacts
            subq = subq.filter(cls.archived.is_(False))

        query = (
            db.session.query(
                sa.column('project_id'),
                sa.column('project_uuid'),
                sa.column('project_title'),
                sa.column('project_timezone'),
                sa.cast(
                    sa.func.date_trunc(
                        'day',
                        sa.func.timezone(
                            sa.column('project_timezone'), sa.column('scanned_at')
                        ),
                    ),
                    sa.Date,
                ).label('scan_date'),
                sa.func.count().label('count'),
            )
            .select_from(subq.subquery())
            .group_by(
                sa.column('project_id'),
                sa.column('project_uuid'),
                sa.column('project_title'),
                sa.column('project_timezone'),
                sa.column('scan_date'),
            )
            .order_by(sa.text('scan_date DESC'))
        )

        # Issued SQL:
        #
        # SELECT
        #   project_id,
        #   project_uuid,
        #   project_title,
        #   project_timezone,
        #   CAST(
        #     date_trunc('day', timezone(project_timezone, scanned_at))
        #     AS DATE
        #   ) AS scan_date,
        #   count(*) AS count
        # FROM (
        #   SELECT
        #     contact_exchange.scanned_at AS scanned_at,
        #     project.id AS project_id,
        #     project.uuid AS project_uuid,
        #     project.timezone AS project_timezone,
        #     project.title AS project_title
        #   FROM contact_exchange, project, ticket_participant
        #   WHERE
        #     contact_exchange.ticket_participant_id = ticket_participant.id
        #     AND ticket_participant.project_id = project.id
        #     AND :user_id = contact_exchange.user_id
        #     AND contact_exchange.archived IS false
        #   ) AS anon_1
        # GROUP BY project_id, project_uuid, project_title, project_timezone, scan_date
        # ORDER BY scan_date DESC

        # The query result has rows of:
        # (project_id, project_uuid, project_title, project_timezone, scan_date, count)
        # with one row per date. It is then transformed into:
        # [
        #   (ProjectId(id, uuid, uuid_b58, title, timezone), [
        #     DateCountContacts(date, count, contacts),
        #     ...  # More dates
        #     ]
        #   ),
        #   ...  # More projects
        #   ]

        # We don't do it here, but this can easily be converted into a dictionary of
        # `{project: dates}` using `dict(result)`

        groups = [
            (
                k,
                [
                    DateCountContacts(
                        r.scan_date,
                        r.count,
                        cls.contacts_for_project_and_date(
                            user, k, r.scan_date, archived
                        ),
                    )
                    for r in g
                ],
            )
            for k, g in groupby(
                query,
                lambda r: ProjectId(
                    id=r.project_id,
                    uuid=r.project_uuid,
                    uuid_b58=uuid_to_base58(r.project_uuid),
                    title=r.project_title,
                    timezone=timezone(r.project_timezone),
                ),
            )
        ]

        return groups

    @classmethod
    def contacts_for_project_and_date(
        cls, user: User, project: Project, date: date_type, archived=False
    ):
        """Return contacts for a given user, project and date."""
        query = cls.query.join(TicketParticipant).filter(
            cls.user == user,
            # For safety always use objects instead of column values. The following
            # expression should have been `Participant.project == project`. However, we
            # are using `id` here because `project` may be an instance of ProjectId
            # returned by `grouped_counts_for`
            TicketParticipant.project_id == project.id,
            sa.cast(
                sa.func.date_trunc(
                    'day', sa.func.timezone(project.timezone.zone, cls.scanned_at)
                ),
                sa.Date,
            )
            == date,
        )
        if not archived:
            # If archived: return everything (contacts including archived contacts)
            # If not archived: return only unarchived contacts
            query = query.filter(cls.archived.is_(False))

        return query

    @classmethod
    def contacts_for_project(cls, user, project, archived=False):
        """Return contacts for a given user and project."""
        query = cls.query.join(TicketParticipant).filter(
            cls.user == user,
            # See explanation for the following expression in
            # `contacts_for_project_and_date`
            TicketParticipant.project_id == project.id,
        )
        if not archived:
            # If archived: return everything (contacts including archived contacts)
            # If not archived: return only unarchived contacts
            query = query.filter(cls.archived.is_(False))
        return query


TicketParticipant.scanning_users = association_proxy('scanned_contacts', 'user')
