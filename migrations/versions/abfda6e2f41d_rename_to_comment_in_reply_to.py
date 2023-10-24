"""Rename to comment.in_reply_to.

Revision ID: abfda6e2f41d
Revises: a42398081979
Create Date: 2020-09-15 17:13:15.240427

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'abfda6e2f41d'
down_revision = 'a42398081979'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.alter_column('comment', 'parent_id', new_column_name='in_reply_to_id')
    op.execute(
        sa.text(
            'ALTER TABLE comment RENAME CONSTRAINT'
            ' comment_parent_id_fkey TO comment_in_reply_to_id;'
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            'ALTER TABLE comment RENAME CONSTRAINT'
            ' comment_in_reply_to_id TO comment_parent_id_fkey;'
        )
    )
    op.alter_column('comment', 'in_reply_to_id', new_column_name='parent_id')
