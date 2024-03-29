"""Added venue, room details.

Revision ID: 1925329c798a
Revises: 316aaa757c8c
Create Date: 2013-11-05 19:48:59.132327

"""

# revision identifiers, used by Alembic.
revision = '1925329c798a'
down_revision = '316aaa757c8c'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.create_table(
        'venue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('description_text', sa.UnicodeText(), nullable=False),
        sa.Column('description_html', sa.UnicodeText(), nullable=False),
        sa.Column('address1', sa.Unicode(length=160), nullable=False),
        sa.Column('address2', sa.Unicode(length=160), nullable=False),
        sa.Column('city', sa.Unicode(length=30), nullable=False),
        sa.Column('state', sa.Unicode(length=30), nullable=False),
        sa.Column('postcode', sa.Unicode(length=20), nullable=False),
        sa.Column('country', sa.Unicode(length=2), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id']),
        sa.UniqueConstraint('proposal_space_id', 'name'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'venue_room',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('venue_id', sa.Integer(), nullable=False),
        sa.Column('description_text', sa.UnicodeText(), nullable=False),
        sa.Column('description_html', sa.UnicodeText(), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.ForeignKeyConstraint(['venue_id'], ['venue.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('venue_id', 'name'),
    )


def downgrade() -> None:
    op.drop_table('venue_room')
    op.drop_table('venue')
