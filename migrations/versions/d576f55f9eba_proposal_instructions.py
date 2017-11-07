"""proposal instructions

Revision ID: d576f55f9eba
Revises: f80ab5d0e11e
Create Date: 2017-10-31 13:03:06.146288

"""

# revision identifiers, used by Alembic.
revision = 'd576f55f9eba'
down_revision = '570f4ea99cda'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal_space', sa.Column('instructions_html', sa.UnicodeText(), nullable=True))
    op.add_column('proposal_space', sa.Column('instructions_text', sa.UnicodeText(), nullable=True))


def downgrade():
    op.drop_column('proposal_space', 'instructions_text')
    op.drop_column('proposal_space', 'instructions_html')
