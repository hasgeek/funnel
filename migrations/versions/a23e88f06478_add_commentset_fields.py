"""Add commentset fields.

Revision ID: a23e88f06478
Revises: 284c10efdbce
Create Date: 2021-03-22 02:54:30.416806
"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = 'a23e88f06478'
down_revision = '284c10efdbce'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

commentset = table(
    'commentset',
    column('id', sa.Integer()),
    column('last_comment_at', sa.TIMESTAMP(timezone=True)),
)

comment = table(
    'comment',
    column('id', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('commentset_id', sa.Integer()),
)


def upgrade() -> None:
    op.add_column(
        'commentset',
        sa.Column('last_comment_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        'commentset_membership',
        sa.Column(
            'is_muted',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('commentset_membership', 'is_muted', server_default=None)

    op.execute(
        commentset.update().values(
            last_comment_at=sa.select(sa.func.max(comment.c.created_at)).where(
                comment.c.commentset_id == commentset.c.id
            )
        )
    )


def downgrade() -> None:
    op.drop_column('commentset_membership', 'is_muted')
    op.drop_column('commentset', 'last_comment_at')
