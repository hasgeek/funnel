"""update null ticket client id

Revision ID: 152442fce4e4
Revises: 570f4ea99cda
Create Date: 2017-10-31 12:42:40.841527

"""

# revision identifiers, used by Alembic.
revision = '152442fce4e4'
down_revision = '570f4ea99cda'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


def upgrade():
    # updating ticket_client_id=1 as we seemed to have missed some
    # records when they were created. They are sitting as NULL in the db.
    # And we need to get rid of them.
    connection = op.get_bind()
    sync_ticket = table(
        'sync_ticket',
        column(u'id', sa.INTEGER()),
        column(u'ticket_client_id', sa.INTEGER())
    )
    connection.execute(
        sync_ticket.update().where(
            sync_ticket.c.ticket_client_id == None
        ).values({
            'ticket_client_id': 1
        })
    )


def downgrade():
    # XXX: No going back from this
    pass
