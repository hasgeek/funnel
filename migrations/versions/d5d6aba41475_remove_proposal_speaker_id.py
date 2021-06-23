"""Remove proposal speaker_id.

Revision ID: d5d6aba41475
Revises: e111dd05e62b
Create Date: 2021-05-11 05:50:32.990176

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd5d6aba41475'
down_revision = 'e111dd05e62b'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('proposal_speaker_id_fkey', 'proposal', type_='foreignkey')
    op.drop_column('proposal', 'speaker_id')


def downgrade():
    op.add_column(
        'proposal',
        sa.Column('speaker_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'proposal_speaker_id_fkey', 'proposal', 'user', ['speaker_id'], ['id']
    )
