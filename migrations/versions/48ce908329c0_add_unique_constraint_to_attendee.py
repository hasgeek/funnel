"""Add unique constraint to attendee.

Revision ID: 48ce908329c0
Revises: 2d73dbe935dc
Create Date: 2015-10-07 16:39:26.501832

"""

# revision identifiers, used by Alembic.
revision = '48ce908329c0'
down_revision = '2d73dbe935dc'

from alembic import op


def upgrade() -> None:
    op.create_unique_constraint(
        'attendee_event_id_participant_id_key',
        'attendee',
        ['event_id', 'participant_id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'attendee_event_id_participant_id_key', 'attendee', type_='unique'
    )
