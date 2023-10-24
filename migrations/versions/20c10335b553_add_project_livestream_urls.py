"""Add project livestream urls.

Revision ID: 20c10335b553
Revises: c11dc931b903
Create Date: 2019-12-13 21:13:14.307378

"""

# revision identifiers, used by Alembic.
revision = '20c10335b553'
down_revision = 'c11dc931b903'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        'project',
        sa.Column(
            'livestream_urls', sa.ARRAY(sa.UnicodeText(), dimensions=1), nullable=True
        ),
    )
    op.alter_column('project', 'livestream_urls', server_default='{}')


def downgrade() -> None:
    op.drop_column('project', 'livestream_urls')
