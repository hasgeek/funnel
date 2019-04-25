"""room bgcolor default

Revision ID: 58588eba8cb8
Revises: 31253f116e1e
Create Date: 2013-11-18 15:46:41.943587

"""

# revision identifiers, used by Alembic.
revision = '58588eba8cb8'
down_revision = '31253f116e1e'

from alembic import op
import sqlalchemy as sa  # NOQA

from funnel.models import VenueRoom


def upgrade():
    connection = op.get_bind()
    room = VenueRoom.__table__
    updt_stmt = room.update().where(room.c.bgcolor == None).values(bgcolor=u'229922')  # NOQA
    connection.execute(updt_stmt)
    op.alter_column('venue_room', 'bgcolor',
               existing_type=sa.VARCHAR(length=6),
               nullable=False)


def downgrade():
    op.alter_column('venue_room', 'bgcolor',
               existing_type=sa.VARCHAR(length=6),
               nullable=True)
