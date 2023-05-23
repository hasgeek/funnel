"""Add title index to event and ticket type.

Revision ID: 416a2f958279
Revises: 2d55f804a4ed
Create Date: 2015-10-15 21:05:30.649687

"""

# revision identifiers, used by Alembic.
revision = '416a2f958279'
down_revision = '2d55f804a4ed'

from alembic import op


def upgrade() -> None:
    op.create_unique_constraint(
        'event_proposal_space_id_title_key', 'event', ['proposal_space_id', 'title']
    )
    op.create_unique_constraint(
        'ticket_type_proposal_space_id_title_key',
        'ticket_type',
        ['proposal_space_id', 'title'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'ticket_type_proposal_space_id_title_key', 'ticket_type', type_='unique'
    )
    op.drop_constraint('event_proposal_space_id_title_key', 'event', type_='unique')
