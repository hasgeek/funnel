"""Shortlink model.

Revision ID: 6835596b1eee
Revises: cad24ab35cc2
Create Date: 2021-06-13 06:08:28.858610

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '6835596b1eee'
down_revision = 'cad24ab35cc2'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name: str = '') -> None:
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    op.create_table(
        'shortlink',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('url', sa.UnicodeText(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_shortlink_url'), 'shortlink', ['url'], unique=False)


def downgrade_() -> None:
    op.drop_index(op.f('ix_shortlink_url'), table_name='shortlink')
    op.drop_table('shortlink')
