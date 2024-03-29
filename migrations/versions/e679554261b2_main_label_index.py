"""Main label index.

Revision ID: e679554261b2
Revises: e2be4ab896d3
Create Date: 2019-05-09 18:55:24.472216

"""

# revision identifiers, used by Alembic.
revision = 'e679554261b2'
down_revision = 'e2be4ab896d3'

from alembic import op


def upgrade() -> None:
    op.create_index(
        op.f('ix_label_main_label_id'), 'label', ['main_label_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_label_main_label_id'), table_name='label')
