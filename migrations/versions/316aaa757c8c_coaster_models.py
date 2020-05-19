"""coaster_models

Revision ID: 316aaa757c8c
Revises: 9d513be1a96
Create Date: 2013-10-02 17:57:54.584815

"""

# revision identifiers, used by Alembic.
revision = '316aaa757c8c'
down_revision = '9d513be1a96'

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


def upgrade():
    op.drop_table('proposal_tags')
    op.drop_table('tag')


def downgrade():
    op.create_table(
        'tag',
        sa.Column(
            'id',
            sa.INTEGER(),
            server_default="nextval('tag_id_seq'::regclass)",
            nullable=False,
        ),
        sa.Column(
            'created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
        sa.Column(
            'updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
        sa.Column('name', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column('title', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='tag_pkey'),
    )
    op.create_table(
        'proposal_tags',
        sa.Column('tag_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('proposal_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint(),
    )
