"""Session edits.

Revision ID: 4aedc1062818
Revises: 55097480a655
Create Date: 2013-11-13 23:10:16.406404

"""

# revision identifiers, used by Alembic.
revision = '4aedc1062818'
down_revision = '55097480a655'

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.alter_column('session', 'start_datetime', new_column_name='start')
    op.alter_column('session', 'end_datetime', new_column_name='end')
    op.alter_column(
        'session', 'venue_room_id', existing_type=sa.INTEGER(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        'session', 'venue_room_id', existing_type=sa.INTEGER(), nullable=False
    )
    op.alter_column('session', 'start', new_column_name='start_datetime')
    op.alter_column('session', 'end', new_column_name='end_datetime')
