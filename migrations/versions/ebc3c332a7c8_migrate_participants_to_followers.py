"""Migrate participants to followers.

Revision ID: ebc3c332a7c8
Revises: 20f830d2fead
Create Date: 2024-03-27 22:13:13.102064

"""

from datetime import datetime
from uuid import uuid4

import rich.progress
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ebc3c332a7c8'
down_revision: str = '20f830d2fead'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


MIGRATED_RECORD_TYPE = 5

account = sa.table(
    'account',
    sa.column('id', sa.Integer()),
    sa.column('name', sa.String()),
)
account_membership = sa.table(
    'account_membership',
    sa.column('id', sa.Uuid()),
    sa.column('created_at', sa.DateTime(timezone=True)),
    sa.column('updated_at', sa.DateTime(timezone=True)),
    sa.column('granted_at', sa.DateTime(timezone=True)),
    sa.column('revoked_at', sa.DateTime(timezone=True)),
    sa.column('record_type', sa.Integer()),
    sa.column('account_id', sa.Integer()),
    sa.column('member_id', sa.Integer()),
    sa.column('granted_by_id', sa.Integer()),
    sa.column('is_admin', sa.Boolean()),
    sa.column('is_owner', sa.Boolean()),
    sa.column('label', sa.String()),
)
project = sa.table(
    'project',
    sa.column('id', sa.Integer()),
    sa.column('account_id', sa.Integer()),
)
project_membership = sa.table(
    'project_membership',
    sa.column('id', sa.Integer()),
    sa.column('created_at', sa.DateTime(timezone=True)),
    sa.column('project_id', sa.Integer()),
    sa.column('member_id', sa.Integer()),
)
rsvp = sa.table(
    'rsvp',
    sa.column('project_id', sa.Integer()),
    sa.column('participant_id', sa.Integer()),
    sa.column('created_at', sa.DateTime(timezone=True)),
)
ticket_participant = sa.table(
    'ticket_participant',
    sa.column('id', sa.Integer()),
    sa.column('project_id', sa.Integer()),
    sa.column('participant_id', sa.Integer()),
    sa.column('created_at', sa.DateTime(timezone=True)),
)


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    conn = op.get_bind()
    # {Account id: {Follower id: Timestamp}}
    followers: dict[int, dict[int, datetime]] = {}

    # Load from project_membership
    project_membership_select = (
        sa.select(
            sa.func.min(project_membership.c.created_at).label('created_at'),
            project_membership.c.member_id.label('member_id'),
            project.c.account_id.label('account_id'),
        )
        .where(project_membership.c.project_id == project.c.id)
        .group_by(project_membership.c.member_id, project.c.account_id)
    )
    count = conn.scalar(
        sa.select(sa.func.count(sa.text('*'))).select_from(
            project_membership_select.subquery()
        )
    )
    items = conn.execute(project_membership_select)
    for item in rich.progress.track(items, "Scanning project crew", total=count):
        followers.setdefault(item.account_id, {}).setdefault(
            item.member_id, item.created_at
        )
        followers[item.account_id][item.member_id] = min(
            item.created_at, followers[item.account_id][item.member_id]
        )

    # Load from RSVP
    rsvp_select = (
        sa.select(
            sa.func.min(rsvp.c.created_at).label('created_at'),
            rsvp.c.participant_id.label('participant_id'),
            project.c.account_id.label('account_id'),
        )
        .where(rsvp.c.project_id == project.c.id)
        .group_by(rsvp.c.participant_id, project.c.account_id)
    )
    count = conn.scalar(
        sa.select(sa.func.count(sa.text('*'))).select_from(rsvp_select.subquery())
    )
    items = conn.execute(rsvp_select)
    for item in rich.progress.track(
        items, "Scanning project registrations", total=count
    ):
        followers.setdefault(item.account_id, {}).setdefault(
            item.participant_id, item.created_at
        )
        followers[item.account_id][item.participant_id] = min(
            item.created_at, followers[item.account_id][item.participant_id]
        )

    # Load from ticket participants
    ticket_select = (
        sa.select(
            sa.func.min(ticket_participant.c.created_at).label('created_at'),
            ticket_participant.c.participant_id.label('participant_id'),
            project.c.account_id.label('account_id'),
        )
        .where(
            ticket_participant.c.participant_id.isnot(None),
            ticket_participant.c.project_id == project.c.id,
        )
        .group_by(ticket_participant.c.participant_id, project.c.account_id)
    )
    count = conn.scalar(
        sa.select(sa.func.count(sa.text('*'))).select_from(ticket_select.subquery())
    )
    items = conn.execute(ticket_select)
    for item in rich.progress.track(items, "Scanning project tickets", total=count):
        followers.setdefault(item.account_id, {}).setdefault(
            item.participant_id, item.created_at
        )
        followers[item.account_id][item.participant_id] = min(
            item.created_at, followers[item.account_id][item.participant_id]
        )

    # Get account names
    accounts: dict[int, str | None] = {
        item.id: item.name
        for item in conn.execute(
            account.select().where(account.c.id.in_(followers.keys()))
        )
    }

    # Make a membership record for each wherever there is no existing record
    for account_id, members in followers.items():
        for member_id, member_since in rich.progress.track(
            members.items(), accounts[account_id] or str(account_id), total=len(members)
        ):
            existing = conn.scalar(
                account_membership.select().where(
                    account_membership.c.account_id == account_id,
                    account_membership.c.member_id == member_id,
                    account_membership.c.revoked_at.is_(None),
                )
            )
            if existing is None:
                conn.execute(
                    account_membership.insert().values(
                        id=uuid4(),
                        created_at=sa.func.now(),
                        updated_at=sa.func.now(),
                        record_type=MIGRATED_RECORD_TYPE,
                        account_id=account_id,
                        member_id=member_id,
                        granted_at=member_since,
                        granted_by_id=member_id,  # Self granted follow
                        is_admin=False,
                        is_owner=False,
                    )
                )


def downgrade_() -> None:
    """Downgrade default database."""
    # Remove all non-admin account members (aka followers)
    op.execute(
        account_membership.delete().where(account_membership.c.is_admin.is_(False))
    )
