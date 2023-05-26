"""Notification models.

Revision ID: 931be3605dc4
Revises: 7f6f417dad02
Create Date: 2020-08-18 11:58:05.088406

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '931be3605dc4'
down_revision = '7f6f417dad02'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.create_table(
        'notification',
        sa.Column('eventid', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('type', sa.Unicode(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('document_uuid', sa.Uuid(), nullable=False),
        sa.Column('fragment_uuid', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('eventid', 'id'),
    )
    op.create_index(
        op.f('ix_notification_document_uuid'),
        'notification',
        ['document_uuid'],
        unique=False,
    )
    op.create_table(
        'notification_preferences',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.Unicode(), nullable=False),
        sa.Column('by_email', sa.Boolean(), nullable=False),
        sa.Column('by_sms', sa.Boolean(), nullable=False),
        sa.Column('by_webpush', sa.Boolean(), nullable=False),
        sa.Column('by_telegram', sa.Boolean(), nullable=False),
        sa.Column('by_whatsapp', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'notification_type'),
    )
    op.create_index(
        op.f('ix_notification_preferences_user_id'),
        'notification_preferences',
        ['user_id'],
        unique=False,
    )
    op.create_table(
        'user_notification',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('eventid', sa.Uuid(), nullable=False),
        sa.Column('notification_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.Unicode(), nullable=False),
        sa.Column('read_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), nullable=False),
        sa.Column('rollupid', sa.Uuid(), nullable=True),
        sa.Column('messageid_email', sa.Unicode(), nullable=True),
        sa.Column('messageid_sms', sa.Unicode(), nullable=True),
        sa.Column('messageid_webpush', sa.Unicode(), nullable=True),
        sa.Column('messageid_telegram', sa.Unicode(), nullable=True),
        sa.Column('messageid_whatsapp', sa.Unicode(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['eventid', 'notification_id'],
            ['notification.eventid', 'notification.id'],
            name='user_notification_eventid_notification_id_fkey',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'eventid'),
    )
    op.create_index(
        op.f('ix_user_notification_is_revoked'),
        'user_notification',
        ['is_revoked'],
        unique=False,
    )
    op.create_index(
        op.f('ix_user_notification_rollupid'),
        'user_notification',
        ['rollupid'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_user_notification_rollupid'), table_name='user_notification')
    op.drop_index(
        op.f('ix_user_notification_is_revoked'), table_name='user_notification'
    )
    op.drop_table('user_notification')
    op.drop_index(
        op.f('ix_notification_preferences_user_id'),
        table_name='notification_preferences',
    )
    op.drop_table('notification_preferences')
    op.drop_index(op.f('ix_notification_document_uuid'), table_name='notification')
    op.drop_table('notification')
