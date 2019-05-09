"""feedback

Revision ID: 5290f9238875
Revises: 4b630fb42760
Create Date: 2013-09-16 21:48:11.320616

"""

# revision identifiers, used by Alembic.
revision = '5290f9238875'
down_revision = '4b630fb42760'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.create_table('proposal_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('auth_type', sa.Integer(), nullable=False),
        sa.Column('id_type', sa.Unicode(length=80), nullable=False),
        sa.Column('userid', sa.Unicode(length=80), nullable=False),
        sa.Column('min_scale', sa.Integer(), nullable=False),
        sa.Column('max_scale', sa.Integer(), nullable=False),
        sa.Column('content', sa.Integer(), nullable=True),
        sa.Column('presentation', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proposal_id', 'auth_type', 'id_type', 'userid')
        )


def downgrade():
    op.drop_table('proposal_feedback')
