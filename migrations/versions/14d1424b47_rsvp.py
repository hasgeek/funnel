"""RSVP

Revision ID: 14d1424b47
Revises: 1c496c114b6
Create Date: 2015-01-30 16:09:42.434798

"""

# revision identifiers, used by Alembic.
revision = '14d1424b47'
down_revision = '1c496c114b6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('rsvp',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.CHAR(length=1), sa.CheckConstraint("status IN ('Y', 'N', 'M', 'A')"), nullable=False),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('proposal_space_id', 'user_id')
        )
    op.add_column('proposal_space', sa.Column('allow_rsvp', sa.Boolean(), nullable=False, server_default='0'))
    op.alter_column('proposal_space', 'allow_rsvp', server_default=None)


def downgrade():
    op.drop_column('proposal_space', 'allow_rsvp')
    op.drop_table('rsvp')
