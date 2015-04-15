"""contact exchange

Revision ID: 589368eb80ff
Revises: 522d776a42ed
Create Date: 2015-04-15 16:17:08.093180

"""

revision = '589368eb80ff'
down_revision = '522d776a42ed'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('contact_exchange',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['participant_id'], ['participant.id'], ),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id', 'user_id', 'proposal_space_id', 'participant_id')
    )


def downgrade():
    op.drop_table('contact_exchange')
