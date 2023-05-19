"""Add proposal sponsor membership.

Revision ID: 277ba2ca9e3e
Revises: 99e99507a595
Create Date: 2022-01-04 16:26:51.717623

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '277ba2ca9e3e'
down_revision = '99e99507a595'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade(engine_name=''):
    # Do not modify. Edit `upgrade_` instead
    globals().get('upgrade_%s' % engine_name, lambda: None)()


def downgrade(engine_name=''):
    # Do not modify. Edit `downgrade_` instead
    globals().get('downgrade_%s' % engine_name, lambda: None)()


def upgrade_():
    op.create_table(
        'proposal_sponsor_membership',
        sa.Column('granted_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('record_type', sa.Integer(), nullable=False),
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('is_promoted', sa.Boolean(), nullable=False),
        sa.Column('label', sa.Unicode(), nullable=True),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('granted_by_id', sa.Integer(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['profile_id'], ['profile.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            'record_type IN (0, 1, 2, 3)',
            name='proposal_sponsor_membership_record_type_check',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_proposal_sponsor_membership_active',
        'proposal_sponsor_membership',
        ['proposal_id', 'profile_id'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.create_index(
        op.f('ix_proposal_sponsor_membership_profile_id'),
        'proposal_sponsor_membership',
        ['profile_id'],
        unique=False,
    )
    op.create_index(
        'ix_proposal_sponsor_membership_seq',
        'proposal_sponsor_membership',
        ['proposal_id', 'seq'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )


def downgrade_():
    op.drop_index(
        'ix_proposal_sponsor_membership_seq',
        table_name='proposal_sponsor_membership',
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.drop_index(
        op.f('ix_proposal_sponsor_membership_profile_id'),
        table_name='proposal_sponsor_membership',
    )
    op.drop_index(
        'ix_proposal_sponsor_membership_active',
        table_name='proposal_sponsor_membership',
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.drop_constraint(
        'proposal_sponsor_membership_record_type_check',
        'proposal_sponsor_membership',
        type_='check',
    )
    op.drop_table('proposal_sponsor_membership')


def upgrade_geoname():
    pass


def downgrade_geoname():
    pass
