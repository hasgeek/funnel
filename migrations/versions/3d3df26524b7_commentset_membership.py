"""commentset membership.

Revision ID: 3d3df26524b7
Revises: daeb6753652a
Create Date: 2020-12-04 13:03:31.208857

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '3d3df26524b7'
down_revision = 'ad5013552ec6'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        'commentset_membership',
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('commentset_id', sa.Integer(), nullable=False),
        sa.Column('last_seen_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['commentset_id'], ['commentset.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_commentset_membership_active',
        'commentset_membership',
        ['commentset_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.create_index(
        op.f('ix_commentset_membership_user_id'),
        'commentset_membership',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_commentset_membership_user_id'), table_name='commentset_membership'
    )
    op.drop_index('ix_commentset_membership_active', table_name='commentset_membership')
    op.drop_table('commentset_membership')
