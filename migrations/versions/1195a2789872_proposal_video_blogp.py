"""Proposal video blogpost.

Revision ID: 1195a2789872
Revises: 3c47ba103724
Create Date: 2014-02-23 02:36:49.955698

"""

# revision identifiers, used by Alembic.
revision = '1195a2789872'
down_revision = '3c47ba103724'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        'proposal',
        sa.Column('blog_post', sa.Unicode(250), server_default='', nullable=False),
    )
    op.alter_column('proposal', 'blog_post', server_default=None)
    op.add_column(
        'proposal',
        sa.Column('preview_video', sa.Unicode(250), server_default='', nullable=False),
    )
    op.alter_column('proposal', 'preview_video', server_default=None)


def downgrade() -> None:
    op.drop_column('proposal', 'preview_video')
    op.drop_column('proposal', 'blog_post')
