# -*- coding: utf-8 -*-

"""add project livestream urls

Revision ID: 20c10335b553
Revises: c11dc931b903
Create Date: 2019-12-13 21:13:14.307378

"""

# revision identifiers, used by Alembic.
revision = '20c10335b553'
down_revision = 'c11dc931b903'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.add_column(
        'project',
        sa.Column(
            'livestream_urls', sa.ARRAY(sa.UnicodeText(), dimensions=1), nullable=True
        ),
    )
    op.alter_column('project', 'livestream_urls', server_default='{}')


def downgrade():
    op.drop_column('project', 'livestream_urls')
