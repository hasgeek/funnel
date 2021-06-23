"""Update ProposalMembership structure.

Revision ID: 82303877b746
Revises: ca578c1b82e8
Create Date: 2021-04-29 02:47:39.590061

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '82303877b746'
down_revision = 'ca578c1b82e8'
branch_labels = None
depends_on = None


def upgrade():
    # This migration assumes there is no existing data in the table
    op.add_column(
        'proposal_membership', sa.Column('is_uncredited', sa.Boolean(), nullable=False)
    )
    op.add_column(
        'proposal_membership', sa.Column('label', sa.Unicode(), nullable=True)
    )
    op.add_column('proposal_membership', sa.Column('seq', sa.Integer(), nullable=False))
    op.create_index(
        'ix_proposal_membership_seq',
        'proposal_membership',
        ['proposal_id', 'seq'],
        unique=True,
        postgresql_where=sa.text('revoked_at IS NULL'),
    )
    op.drop_column('proposal_membership', 'is_reviewer')
    op.drop_column('proposal_membership', 'is_presenter')


def downgrade():
    # This migration assumes there is no existing data in the table
    op.add_column(
        'proposal_membership',
        sa.Column('is_presenter', sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.add_column(
        'proposal_membership',
        sa.Column('is_reviewer', sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.drop_index('ix_proposal_membership_seq', table_name='proposal_membership')
    op.drop_column('proposal_membership', 'seq')
    op.drop_column('proposal_membership', 'label')
    op.drop_column('proposal_membership', 'is_uncredited')
