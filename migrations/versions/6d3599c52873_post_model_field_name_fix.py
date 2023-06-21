"""Post model field name fix.

Revision ID: 6d3599c52873
Revises: a1ab7bd78649
Create Date: 2020-07-23 12:47:40.474840

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '6d3599c52873'
down_revision = 'a1ab7bd78649'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.add_column('post', sa.Column('body_html', sa.UnicodeText(), nullable=False))
    op.add_column('post', sa.Column('body_text', sa.UnicodeText(), nullable=False))
    op.add_column('post', sa.Column('is_pinned', sa.Boolean(), nullable=False))
    op.add_column('post', sa.Column('name', sa.Unicode(length=250), nullable=False))
    op.add_column('post', sa.Column('title', sa.Unicode(length=250), nullable=False))
    op.add_column('post', sa.Column('url_id', sa.Integer(), nullable=False))
    op.add_column(
        'post', sa.Column('visibility_state', sa.SmallInteger(), nullable=False)
    )
    op.create_index(op.f('ix_post_state'), 'post', ['state'], unique=False)
    op.create_index(
        op.f('ix_post_visibility_state'), 'post', ['visibility_state'], unique=False
    )
    op.drop_column('post', 'message_text')
    op.drop_column('post', 'message_html')
    op.drop_column('post', 'visibility')
    op.drop_column('post', 'pinned')


def downgrade() -> None:
    op.add_column(
        'post', sa.Column('pinned', sa.BOOLEAN(), autoincrement=False, nullable=False)
    )
    op.add_column(
        'post',
        sa.Column('visibility', sa.SMALLINT(), autoincrement=False, nullable=False),
    )
    op.add_column(
        'post',
        sa.Column('message_html', sa.TEXT(), autoincrement=False, nullable=False),
    )
    op.add_column(
        'post',
        sa.Column('message_text', sa.TEXT(), autoincrement=False, nullable=False),
    )
    op.drop_index(op.f('ix_post_visibility_state'), table_name='post')
    op.drop_index(op.f('ix_post_state'), table_name='post')
    op.drop_column('post', 'visibility_state')
    op.drop_column('post', 'url_id')
    op.drop_column('post', 'title')
    op.drop_column('post', 'name')
    op.drop_column('post', 'is_pinned')
    op.drop_column('post', 'body_text')
    op.drop_column('post', 'body_html')
