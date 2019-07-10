"""Featured project flag

Revision ID: ea20c403b240
Revises: c38fa391613f
Create Date: 2019-06-05 12:38:15.928874

"""

# revision identifiers, used by Alembic.
revision = 'ea20c403b240'
down_revision = 'c38fa391613f'

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column('project', sa.Column('featured', sa.Boolean(),
        nullable=False, server_default=sa.sql.expression.false()))
    op.alter_column('project', 'featured', server_default=None)


def downgrade():
    op.drop_column('project', 'featured')
