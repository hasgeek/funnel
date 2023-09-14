"""Add SponsorMembership.

Revision ID: bd465803af3a
Revises: c3483d25178c
Create Date: 2021-04-22 05:02:07.027690

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'bd465803af3a'
down_revision = 'c3483d25178c'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        'sponsor_membership',
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('is_promoted', sa.Boolean(), nullable=False),
        sa.Column('label', sa.Unicode(), nullable=True),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['profile_id'], ['profile.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            'record_type IN (0, 1, 2, 3)', name='sponsor_membership_record_type_check'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_sponsor_membership_active',
        'sponsor_membership',
        ['project_id', 'profile_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.create_index(
        op.f('ix_sponsor_membership_profile_id'),
        'sponsor_membership',
        ['profile_id'],
        unique=False,
    )
    op.create_index(
        'ix_sponsor_membership_seq',
        'sponsor_membership',
        ['project_id', 'seq'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_sponsor_membership_seq', table_name='sponsor_membership')
    op.drop_index(
        op.f('ix_sponsor_membership_profile_id'), table_name='sponsor_membership'
    )
    op.drop_index('ix_sponsor_membership_active', table_name='sponsor_membership')
    op.drop_constraint(
        'sponsor_membership_record_type_check', 'sponsor_membership', type_='check'
    )
    op.drop_table('sponsor_membership')
