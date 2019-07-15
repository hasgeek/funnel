# -*- coding: utf-8 -*-

"""Added location to proposal

Revision ID: 4dbf686f4380
Revises: 1fcee2e6280
Create Date: 2013-11-08 23:35:43.433963

"""

# revision identifiers, used by Alembic.
revision = '4dbf686f4380'
down_revision = '1fcee2e6280'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.add_column(
        'proposal',
        sa.Column(
            'location',
            sa.Unicode(length=80),
            server_default=sa.text(u"''"),
            nullable=False,
        ),
    )
    op.alter_column('proposal', 'location', server_default=None)


def downgrade():
    op.drop_column('proposal', 'location')
