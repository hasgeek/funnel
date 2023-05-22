"""Add membership models.

Revision ID: 8829241430b6
Revises: 41b3af7e4449
Create Date: 2020-04-21 01:40:41.323838

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8829241430b6'
down_revision = '41b3af7e4449'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade():
    op.create_table(
        'organization_membership',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_owner', sa.Boolean(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(
            ['organization_id'], ['organization.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_organization_membership_user_id'),
        'organization_membership',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_organization_membership_active'),
        'organization_membership',
        ['organization_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.create_table(
        'project_crew_membership',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_editor', sa.Boolean(), nullable=False),
        sa.Column('is_concierge', sa.Boolean(), nullable=False),
        sa.Column('is_usher', sa.Boolean(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=True),
        sa.CheckConstraint(
            'is_editor IS TRUE OR is_concierge IS TRUE OR is_usher IS TRUE',
            name='project_crew_membership_has_role',
        ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_project_crew_membership_user_id'),
        'project_crew_membership',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_project_crew_membership_active'),
        'project_crew_membership',
        ['project_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.create_table(
        'proposal_membership',
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('is_reviewer', sa.Boolean(), nullable=False),
        sa.Column('is_presenter', sa.Boolean(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            'is_reviewer IS true OR is_presenter IS true',
            name='proposal_membership_has_role',
        ),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_proposal_membership_user_id'),
        'proposal_membership',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_proposal_membership_active'),
        'proposal_membership',
        ['proposal_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )


def downgrade():
    op.drop_index(
        op.f('ix_proposal_membership_active'), table_name='proposal_membership'
    )
    op.drop_index(
        op.f('ix_proposal_membership_user_id'), table_name='proposal_membership'
    )
    op.drop_table('proposal_membership')
    op.drop_index(
        op.f('ix_project_crew_membership_active'), table_name='project_crew_membership'
    )
    op.drop_index(
        op.f('ix_project_crew_membership_user_id'), table_name='project_crew_membership'
    )
    op.drop_table('project_crew_membership')
    op.drop_index(
        op.f('ix_organization_membership_active'), table_name='organization_membership'
    )
    op.drop_index(
        op.f('ix_organization_membership_user_id'), table_name='organization_membership'
    )
    op.drop_table('organization_membership')
