"""event_models

Revision ID: 2fc2f1b5d428
Revises: 447728ca6d2e
Create Date: 2015-04-14 22:02:02.878532

"""

revision = '2fc2f1b5d428'
down_revision = '447728ca6d2e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('ticket_type',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('participant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('fullname', sa.Unicode(length=80), nullable=False),
        sa.Column('email', sa.Unicode(length=80), nullable=False),
        sa.Column('phone', sa.Unicode(length=80), nullable=True),
        sa.Column('twitter', sa.Unicode(length=80), nullable=True),
        sa.Column('job_title', sa.Unicode(length=80), nullable=True),
        sa.Column('company', sa.Unicode(length=80), nullable=True),
        sa.Column('city', sa.Unicode(length=80), nullable=True),
        sa.Column('puk', sa.Unicode(length=44), nullable=False),
        sa.Column('key', sa.Unicode(length=44), nullable=False),
        sa.Column('badge_printed', sa.Boolean(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proposal_space_id', 'email'),
        sa.UniqueConstraint('key'),
        sa.UniqueConstraint('puk')
    )
    op.create_table('event_ticket_type',
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('ticket_type_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_type.id'], )
    )
    op.create_table('sync_ticket',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('ticket_no', sa.Unicode(length=80), nullable=False),
        sa.Column('order_no', sa.Unicode(length=80), nullable=False),
        sa.Column('ticket_type_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['participant_id'], ['participant.id'], ),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_type.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_no')
    )
    op.create_table('attendee',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('checked_in', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
        sa.ForeignKeyConstraint(['participant_id'], ['participant.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('attendee')
    op.drop_table('sync_ticket')
    op.drop_table('event_ticket_type')
    op.drop_table('participant')
    op.drop_table('event')
    op.drop_table('ticket_type')
