from __future__ import annotations

from collections import namedtuple
from itertools import groupby
from typing import Iterable, Optional, Set

from sqlalchemy.ext.associationproxy import association_proxy

from coaster.utils import uuid_to_base58

from ..typing import OptionalMigratedTables
from . import RoleMixin, TimestampMixin, db
from .project import Project
from .sync_ticket import TicketParticipant
from .user import User

__all__ = ['ContactExchange']


# Named tuples for returning contacts grouped by project and date
ProjectId = namedtuple('ProjectId', ['id', 'uuid', 'uuid_b58', 'title', 'timezone'])
DateCountContacts = namedtuple('DateCountContacts', ['date', 'count', 'contacts'])


class ContactExchange(TimestampMixin, RoleMixin, db.Model):
    """Model to track who scanned whose badge, in which project."""

    __tablename__ = 'contact_exchange'
    #: User who scanned this contact
    user_id = db.Column(
        None, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True
    )
    user = db.relationship(
        User,
        backref=db.backref(
            'scanned_contacts',
            lazy='dynamic',
            order_by='ContactExchange.scanned_at.desc()',
            passive_deletes=True,
        ),
    )
    #: Participant whose contact was scanned
    ticket_participant_id = db.Column(
        None,
        db.ForeignKey('ticket_participant.id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
    )
    ticket_participant = db.relationship(
        TicketParticipant, backref=db.backref('scanned_contacts', passive_deletes=True)
    )
    #: Datetime at which the scan happened
    scanned_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )
    #: Note recorded by the user (plain text)
    description = db.Column(db.UnicodeText, nullable=False, default='')
    #: Archived flag
    archived = db.Column(db.Boolean, nullable=False, default=False)

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

    def roles_for(self, actor: Optional[User], anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        if actor is not None:
            if actor == self.user:
                roles.add('owner')
            if actor == self.ticket_participant.user:
                roles.add('subject')
        return roles

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
        ticket_participant_ids = {
            ce.ticket_participant_id for ce in new_user.scanned_contacts
        }
        for ce in old_user.scanned_contacts:
            if ce.ticket_participant_id not in ticket_participant_ids:
                ce.user = new_user
            else:
                # Discard duplicate contact exchange
                db.session.delete(ce)
        return None

    @classmethod
    def grouped_counts_for(cls, user, archived=False):
        """Return count of contacts grouped by project and date."""
        query = db.session.query(
            cls.scanned_at, Project.id, Project.uuid, Project.timezone, Project.title
        ).filter(
            cls.ticket_participant_id == TicketParticipant.id,
            TicketParticipant.project_id == Project.id,
            cls.user == user,
        )

        if not archived:
            # If archived == True: return everything (contacts including archived contacts)
            # if archived == False: return only unarchived contacts
            query = query.filter(cls.archived == False)

        # from_self turns `SELECT columns` into `SELECT new_columns FROM (SELECT columns)`
        query = (
            query.from_self(
                Project.id.label('id'),
                Project.uuid.label('uuid'),
                Project.title.label('title'),
                Project.timezone.label('timezone'),
                db.cast(
                    db.func.date_trunc(
                        'day', db.func.timezone(Project.timezone, cls.scanned_at)
                    ),
                    db.Date,
                ).label('date'),
                db.func.count().label('count'),
            )
            .group_by(
                db.text('id'),
                db.text('uuid'),
                db.text('title'),
                db.text('timezone'),
                db.text('date'),
            )
            .order_by(db.text('date DESC'))
        )

        # Issued SQL:
        #
        # SELECT
        #   project_id AS id,
        #   project_uuid AS uuid,
        #   project_title AS title,
        #   project_timezone AS "timezone",
        #   date_trunc('day', timezone("timezone", contact_exchange_scanned_at))::date AS date,
        #   count(*) AS count
        # FROM (
        #   SELECT
        #     contact_exchange.scanned_at AS contact_exchange_scanned_at,
        #     project.id AS project_id,
        #     project.uuid AS project_uuid,
        #     project.title AS project_title,
        #     project.timezone AS project_timezone
        #   FROM contact_exchange, ticket_participant, project
        #   WHERE
        #     contact_exchange.ticket_participant_id = ticket_participant.id
        #     AND ticket_participant.project_id = project.id
        #     AND contact_exchange.user_id = :user_id
        #   ) AS anon_1
        # GROUP BY id, uuid, title, timezone, date
        # ORDER BY date DESC;

        # Our query result looks like this:
        # [(id, uuid, title, timezone, date, count), ...]
        # where (id, uuid, title, timezone) repeat for each date
        #
        # Transform it into this:
        # [
        #   (ProjectId(id, uuid, uuid_b58, title, timezone), [
        #     DateCountContacts(date, count, contacts),
        #     ...  # More dates
        #     ]
        #   ),
        #   ...  # More projects
        #   ]

        # We don't do it here, but this can easily be converted into a dictionary of {project: dates}:
        # >>> OrderedDict(result)  # Preserve order with most recent projects first
        # >>> dict(result)         # Don't preserve order

        groups = [
            (
                k,
                [
                    DateCountContacts(
                        r.date,
                        r.count,
                        cls.contacts_for_project_and_date(user, k, r.date, archived),
                    )
                    for r in g
                ],
            )
            for k, g in groupby(
                query,
                lambda r: ProjectId(
                    r.id, r.uuid, uuid_to_base58(r.uuid), r.title, r.timezone
                ),
            )
        ]

        return groups

    @classmethod
    def contacts_for_project_and_date(cls, user, project, date, archived=False):
        """Return contacts for a given user, project and date."""
        query = cls.query.join(TicketParticipant).filter(
            cls.user == user,
            # For safety always use objects instead of column values. The following expression
            # should have been `Participant.project == project`. However, we are using `id` here
            # because `project` may be an instance of ProjectId returned by `grouped_counts_for`
            TicketParticipant.project_id == project.id,
            db.cast(
                db.func.date_trunc(
                    'day', db.func.timezone(project.timezone.zone, cls.scanned_at)
                ),
                db.Date,
            )
            == date,
        )
        if not archived:
            # If archived == True: return everything (contacts including archived contacts)
            # if archived == False: return only unarchived contacts
            query = query.filter(cls.archived == False)

        return query

    @classmethod
    def contacts_for_project(cls, user, project, archived=False):
        """Return contacts for a given user and project."""
        query = cls.query.join(TicketParticipant).filter(
            cls.user == user,
            # See explanation for the following expression in `contacts_for_project_and_date`
            TicketParticipant.project_id == project.id,
        )
        if not archived:
            # If archived == True: return everything (contacts including archived contacts)
            # if archived == False: return only unarchived contacts
            query = query.filter(cls.archived == False)
        return query


TicketParticipant.scanning_users = association_proxy('scanned_contacts', 'user')
