# -*- coding: utf-8 -*-

"""Index Team.orgid

Revision ID: 411fc4124fb5
Revises: 436114dffa00
Create Date: 2014-12-03 02:33:37.924291

"""

# revision identifiers, used by Alembic.
revision = '411fc4124fb5'
down_revision = '436114dffa00'

from alembic import op


def upgrade():
    with op.batch_alter_table('team', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_team_orgid'), ['orgid'], unique=False)


def downgrade():
    with op.batch_alter_table('team', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_team_orgid'))
