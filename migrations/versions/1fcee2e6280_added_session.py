"""Added session

Revision ID: 1fcee2e6280
Revises: 1925329c798a
Create Date: 2013-11-08 19:24:18.721591

"""

# revision identifiers, used by Alembic.
revision = '1fcee2e6280'
down_revision = '1925329c798a'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.create_table('session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('description_text', sa.UnicodeText(), nullable=False),
        sa.Column('description_html', sa.UnicodeText(), nullable=False),
        sa.Column('speaker_bio_text', sa.UnicodeText(), nullable=False),
        sa.Column('speaker_bio_html', sa.UnicodeText(), nullable=False),
        sa.Column('proposal_id', sa.Integer(), nullable=True),
        sa.Column('start_datetime', sa.DateTime(), nullable=False),
        sa.Column('end_datetime', sa.DateTime(), nullable=False),
        sa.Column('venue_room_id', sa.Integer(), nullable=False),
        sa.Column('is_break', sa.Boolean(), nullable=False),
        sa.Column('url_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.ForeignKeyConstraint(['venue_room_id'], ['venue_room.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proposal_space_id', 'url_id')
        )
    op.add_column('venue_room', sa.Column('bgcolor', sa.Unicode(length=6), nullable=True))


def downgrade():
    op.drop_table('session')
    op.drop_column('venue_room', 'bgcolor')
