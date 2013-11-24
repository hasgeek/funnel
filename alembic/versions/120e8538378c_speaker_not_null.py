"""speaker not null

Revision ID: 120e8538378c
Revises: 6f98e24760d
Create Date: 2013-11-25 02:06:32.652370

"""

# revision identifiers, used by Alembic.
revision = '120e8538378c'
down_revision = '6f98e24760d'

from alembic import op
import sqlalchemy as sa

from sqlalchemy.sql import select, bindparam
from funnel.models import Session


def upgrade():
    connection = op.get_bind()

    session = Session.__table__

    connection.execute(session.update().where(session.c.speaker == None).values(speaker=u""))
    op.alter_column('session', 'speaker',
        existing_type=sa.VARCHAR(length=200),
        nullable=False)


def downgrade():
    op.alter_column('session', 'speaker',
        existing_type=sa.VARCHAR(length=200),
        nullable=True)

    connection = op.get_bind()

    session = Session.__table__
    
    connection.execute(session.update().where(session.c.speaker == u"").values(speaker=None))
