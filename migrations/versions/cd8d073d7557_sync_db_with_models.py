# -*- coding: utf-8 -*-

"""Sync DB with models

Revision ID: cd8d073d7557
Revises: 71f961809275
Create Date: 2018-11-07 14:50:09.572953

"""

# revision identifiers, used by Alembic.
revision = 'cd8d073d7557'
down_revision = '71f961809275'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.alter_column(
        'event', 'title', existing_type=sa.VARCHAR(length=250), nullable=False
    )
    op.alter_column(
        'sync_ticket', 'ticket_client_id', existing_type=sa.INTEGER(), nullable=False
    )
    op.alter_column(
        'ticket_type', 'title', existing_type=sa.VARCHAR(length=250), nullable=False
    )


def downgrade():
    op.alter_column(
        'ticket_type', 'title', existing_type=sa.VARCHAR(length=250), nullable=True
    )
    op.alter_column(
        'sync_ticket', 'ticket_client_id', existing_type=sa.INTEGER(), nullable=True
    )
    op.alter_column(
        'event', 'title', existing_type=sa.VARCHAR(length=250), nullable=True
    )
