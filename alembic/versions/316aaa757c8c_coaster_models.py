"""coaster_models

Revision ID: 316aaa757c8c
Revises: 9d513be1a96
Create Date: 2013-10-02 17:57:54.584815

"""

# revision identifiers, used by Alembic.
revision = '316aaa757c8c'
down_revision = '9d513be1a96'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.drop_table(u'proposal_tags')
    op.drop_table(u'tag')


def downgrade():
    op.create_table(u'tag',
    sa.Column(u'id', sa.INTEGER(), server_default="nextval('tag_id_seq'::regclass)", nullable=False),
    sa.Column(u'created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column(u'updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column(u'name', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
    sa.Column(u'title', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint(u'id', name=u'tag_pkey')
    )
    op.create_table(u'proposal_tags',
    sa.Column(u'tag_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column(u'proposal_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint()
    )
