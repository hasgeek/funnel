"""Adding commentset membership models.

Revision ID: d0069d5e6787
Revises: daeb6753652a
Create Date: 2020-12-03 11:49:54.132697

"""

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd0069d5e6787'
down_revision = 'daeb6753652a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'commentset_membership',
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('is_subscriber', sa.Boolean(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=True),
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_commentset_membership_active',
        'commentset_membership',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.create_index(
        op.f('ix_commentset_membership_user_id'),
        'commentset_membership',
        ['user_id'],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f('ix_commentset_membership_user_id'), table_name='commentset_membership'
    )
    op.drop_index('ix_commentset_membership_active', table_name='commentset_membership')
    op.drop_table('commentset_membership')
