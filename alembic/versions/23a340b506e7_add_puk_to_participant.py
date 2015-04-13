"""add_puk_to_participant

Revision ID: 23a340b506e7
Revises: 3d5811400a38
Create Date: 2015-04-11 17:13:41.358429

"""

revision = '23a340b506e7'
down_revision = '3d5811400a38'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('participant', sa.Column('puk', sa.Unicode(length=44), nullable=True))
    op.alter_column('participant', 'badge_printed',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    op.alter_column('participant', 'key',
               existing_type=sa.VARCHAR(length=44),
               nullable=False)
    op.create_unique_constraint(None, 'participant', ['puk'])


def downgrade():
    op.drop_constraint(None, 'participant', type_='unique')
    op.alter_column('participant', 'key',
               existing_type=sa.VARCHAR(length=44),
               nullable=True)
    op.alter_column('participant', 'badge_printed',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.drop_column('participant', 'puk')
