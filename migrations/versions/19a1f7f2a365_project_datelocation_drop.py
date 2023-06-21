"""Project datelocation drop.

Revision ID: 19a1f7f2a365
Revises: 9a0d8fa7da29
Create Date: 2018-12-04 21:00:12.445853

"""

revision = '19a1f7f2a365'
down_revision = '9a0d8fa7da29'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.drop_column('project', 'datelocation')


def downgrade() -> None:
    op.add_column(
        'project',
        sa.Column(
            'datelocation',
            sa.VARCHAR(length=50),
            autoincrement=False,
            server_default='',
            nullable=False,
        ),
    )
