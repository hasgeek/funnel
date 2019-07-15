# -*- coding: utf-8 -*-

"""add ticket client

Revision ID: 22fb4e1e3139
Revises: 40c4ad7c0909
Create Date: 2015-05-13 16:51:14.399678

"""

revision = '22fb4e1e3139'
down_revision = '40c4ad7c0909'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.create_table(
        'ticket_client',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('client_event_id', sa.Unicode(length=80), nullable=False),
        sa.Column('client_id', sa.Unicode(length=80), nullable=False),
        sa.Column('client_secret', sa.Unicode(length=80), nullable=False),
        sa.Column('client_access_token', sa.Unicode(length=80), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column(
        u'sync_ticket', sa.Column('ticket_client_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'sync_ticket_ticket_client_id',
        'sync_ticket',
        'ticket_client',
        ['ticket_client_id'],
        ['id'],
    )


def downgrade():
    op.drop_constraint(
        'sync_ticket_ticket_client_id', 'sync_ticket', type_='foreignkey'
    )
    op.drop_column(u'sync_ticket', 'ticket_client_id')
    op.drop_table('ticket_client')
