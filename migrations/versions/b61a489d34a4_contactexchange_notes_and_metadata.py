# -*- coding: utf-8 -*-

"""ContactExchange notes and metadata

Revision ID: b61a489d34a4
Revises: 1829e53eba75
Create Date: 2019-06-22 10:28:13.775099

"""

# revision identifiers, used by Alembic.
revision = 'b61a489d34a4'
down_revision = '1829e53eba75'

import sqlalchemy as sa  # NOQA
from alembic import op
from sqlalchemy.sql import column, table

contact_exchange = table(
    'contact_exchange',
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('scanned_at', sa.TIMESTAMP(timezone=True)),
)


def upgrade():
    op.add_column(
        'contact_exchange',
        sa.Column(
            'archived',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('contact_exchange', 'archived', server_default=None)

    op.add_column(
        'contact_exchange',
        sa.Column('scanned_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(
        contact_exchange.update().values({'scanned_at': contact_exchange.c.created_at})
    )
    op.alter_column('contact_exchange', 'scanned_at', nullable=False)

    op.add_column(
        'contact_exchange',
        sa.Column('description', sa.UnicodeText(), nullable=False, server_default=''),
    )
    op.alter_column('contact_exchange', 'description', server_default=None)


def downgrade():
    op.drop_column('contact_exchange', 'description')
    op.drop_column('contact_exchange', 'scanned_at')
    op.drop_column('contact_exchange', 'archived')
