"""Keep revoked timestamp.

Revision ID: 4845fd12dbfd
Revises: abfda6e2f41d
Create Date: 2020-09-18 00:53:48.765903

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '4845fd12dbfd'
down_revision = 'abfda6e2f41d'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        'user_notification',
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        op.f('ix_user_notification_revoked_at'),
        'user_notification',
        ['revoked_at'],
        unique=False,
    )

    op.execute(
        sa.text(
            'UPDATE user_notification SET revoked_at = updated_at'
            ' WHERE is_revoked IS TRUE;'
        )
    )

    op.drop_index('ix_user_notification_is_revoked', table_name='user_notification')
    op.drop_column('user_notification', 'is_revoked')


def downgrade() -> None:
    op.add_column(
        'user_notification',
        sa.Column(
            'is_revoked',
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )

    op.execute(
        sa.text(
            'UPDATE user_notification SET is_revoked = TRUE'
            ' WHERE revoked_at IS NOT NULL;'
        )
    )

    op.alter_column('user_notification', 'is_revoked', server_default=None)

    op.create_index(
        'ix_user_notification_is_revoked',
        'user_notification',
        ['is_revoked'],
        unique=False,
    )
    op.drop_index(
        op.f('ix_user_notification_revoked_at'), table_name='user_notification'
    )
    op.drop_column('user_notification', 'revoked_at')
