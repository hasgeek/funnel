"""Remove password reset request model.

Revision ID: dcd0870c24cc
Revises: 0d462811a07f
Create Date: 2020-08-02 02:02:43.959488

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dcd0870c24cc'
down_revision = '0d462811a07f'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.drop_index(
        'ix_auth_password_reset_request_user_id',
        table_name='auth_password_reset_request',
    )
    op.drop_table('auth_password_reset_request')


def downgrade() -> None:
    op.create_table(
        'auth_password_reset_request',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            'reset_code', sa.VARCHAR(length=44), autoincrement=False, nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], name='auth_password_reset_request_user_id_fkey'
        ),
        sa.PrimaryKeyConstraint('id', name='auth_password_reset_request_pkey'),
    )
    op.create_index(
        'ix_auth_password_reset_request_user_id',
        'auth_password_reset_request',
        ['user_id'],
        unique=False,
    )
