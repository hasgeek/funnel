"""contact_exchange

Revision ID: 2c64e60b80a
Revises: 522d776a42ed
Create Date: 2015-04-15 17:04:28.666090

"""

revision = '2c64e60b80a'
down_revision = '522d776a42ed'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('contact_exchange',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('proposal_space_id', sa.Integer(), nullable=True),
        sa.Column('participant_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['participant_id'], ['participant.id'], ),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'proposal_space_id', 'participant_id')
        )


def downgrade():
    op.drop_table('contact_exchange')
