"""add membership models

Revision ID: 8cb98498a659
Revises: e2be4ab896d3
Create Date: 2019-05-07 00:15:33.384995

"""

# revision identifiers, used by Alembic.
revision = '8cb98498a659'
down_revision = 'e2be4ab896d3'

from alembic import op
import sqlalchemy as sa  # NOQA
from sqlalchemy_utils import UUIDType


def upgrade():
    op.create_table('profile_admin_membership',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_owner', sa.Boolean(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profile.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    op.create_index(op.f('ix_profile_admin_membership_user_id'), 'profile_admin_membership', ['user_id'], unique=False)
    op.create_index('profile_admin_membership_active', 'profile_admin_membership', ['profile_id', 'user_id'], unique=True, postgresql_where=sa.text(u'revoked_at IS NOT NULL'))

    op.create_table('project_crew_membership',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_editor', sa.Boolean(), nullable=False),
        sa.Column('is_concierge', sa.Boolean(), nullable=False),
        sa.Column('is_usher', sa.Boolean(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.CheckConstraint(u'is_editor IS TRUE OR is_concierge IS TRUE OR is_usher IS TRUE', name='project_crew_membership_has_role'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    op.create_index(op.f('ix_project_crew_membership_user_id'), 'project_crew_membership', ['user_id'], unique=False)
    op.create_index('project_crew_membership_active', 'project_crew_membership', ['project_id', 'user_id'], unique=True, postgresql_where=sa.text(u'revoked_at IS NOT NULL'))


def downgrade():
    op.drop_index('project_crew_membership_active', table_name='project_crew_membership')
    op.drop_index(op.f('ix_project_crew_membership_user_id'), table_name='project_crew_membership')
    op.drop_table('project_crew_membership')

    op.drop_index('profile_admin_membership_active', table_name='profile_admin_membership')
    op.drop_index(op.f('ix_profile_admin_membership_user_id'), table_name='profile_admin_membership')
    op.drop_table('profile_admin_membership')
