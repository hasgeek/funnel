"""Site membership models.

Revision ID: 34a95ee0c3a0
Revises: 887db555cca9
Create Date: 2020-05-14 16:32:52.553441

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '34a95ee0c3a0'
down_revision = '887db555cca9'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade():
    op.create_table(
        'site_membership',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('is_comment_moderator', sa.Boolean(), nullable=False),
        sa.Column('is_user_moderator', sa.Boolean(), nullable=False),
        sa.Column('is_site_editor', sa.Boolean(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            'is_comment_moderator IS true OR is_user_moderator IS true OR is_site_editor IS true',
            name='site_membership_has_role',
        ),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_site_membership_active',
        'site_membership',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.create_index(
        op.f('ix_site_membership_user_id'), 'site_membership', ['user_id'], unique=False
    )


def downgrade():
    op.drop_index(op.f('ix_site_membership_user_id'), table_name='site_membership')
    op.drop_index('ix_site_membership_active', table_name='site_membership')
    op.drop_table('site_membership')
