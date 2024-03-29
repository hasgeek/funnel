"""Room bgcolor default.

Revision ID: 58588eba8cb8
Revises: 31253f116e1e
Create Date: 2013-11-18 15:46:41.943587

"""

# revision identifiers, used by Alembic.
revision = '58588eba8cb8'
down_revision = '31253f116e1e'

import sqlalchemy as sa
from alembic import op

venue_room = sa.table('venue_room', sa.column('bgcolor', sa.String()))


def upgrade() -> None:
    op.execute(
        venue_room.update()
        .where(venue_room.c.bgcolor.is_(None))
        .values(bgcolor='229922')
    )
    op.alter_column(
        'venue_room', 'bgcolor', existing_type=sa.VARCHAR(length=6), nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        'venue_room', 'bgcolor', existing_type=sa.VARCHAR(length=6), nullable=True
    )
