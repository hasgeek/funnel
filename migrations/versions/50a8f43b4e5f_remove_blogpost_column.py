"""Remove blogpost column.

Revision ID: 50a8f43b4e5f
Revises: 411fc4124fb5
Create Date: 2014-12-03 03:46:34.962222

"""

# revision identifiers, used by Alembic.
revision = '50a8f43b4e5f'
down_revision = '411fc4124fb5'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.drop_column('blog_post')


def downgrade() -> None:
    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'blog_post',
                sa.VARCHAR(length=250),
                autoincrement=False,
                nullable=False,
                server_default="''",
            )
        )
        batch_op.alter_column('blog_post', server_default=None)
