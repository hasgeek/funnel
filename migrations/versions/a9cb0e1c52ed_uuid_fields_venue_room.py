"""Uuid fields venue_room.

Revision ID: a9cb0e1c52ed
Revises: e417a13e136d
Create Date: 2019-02-11 20:40:46.581735

"""

# revision identifiers, used by Alembic.
revision = 'a9cb0e1c52ed'
down_revision = 'e417a13e136d'

from uuid import uuid4

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

venue_room = table(
    'venue_room', column('id', sa.Integer()), column('uuid', postgresql.UUID())
)


def upgrade():
    conn = op.get_bind()

    op.add_column('venue_room', sa.Column('uuid', postgresql.UUID(), nullable=True))
    items = conn.execute(sa.select(venue_room.c.id))
    for item in items:
        conn.execute(
            sa.update(venue_room).where(venue_room.c.id == item.id).values(uuid=uuid4())
        )
    op.alter_column('venue_room', 'uuid', nullable=False)
    op.create_unique_constraint('venue_room_uuid_key', 'venue_room', ['uuid'])


def downgrade():
    op.drop_constraint('venue_room_uuid_key', 'venue_room', type_='unique')
    op.drop_column('venue_room', 'uuid')
