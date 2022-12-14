"""Remove obsolete Proposal fields.

Revision ID: c3483d25178c
Revises: a23e88f06478
Create Date: 2021-04-05 20:36:55.734125
"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3483d25178c'
down_revision = 'a23e88f06478'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

# This migration removes the obsolete proposal fields that were deprecated four months
# ago (Dec 2020) in migration ad5013552ec6. The deletion in this migration is permanent.
# The email, phone and location fields are not redundant and will be lost.


def upgrade():
    op.drop_index('ix_proposal_email_address_id', table_name='proposal')
    op.drop_constraint('proposal_email_address_id_fkey', 'proposal', type_='foreignkey')
    op.drop_column('proposal', 'outline_html')
    op.drop_column('proposal', 'slides')
    op.drop_column('proposal', 'abstract_html')
    op.drop_column('proposal', 'email_address_id')
    op.drop_column('proposal', 'location')
    op.drop_column('proposal', 'abstract_text')
    op.drop_column('proposal', 'phone')
    op.drop_column('proposal', 'bio_html')
    op.drop_column('proposal', 'bio_text')
    op.drop_column('proposal', 'links')
    op.drop_column('proposal', 'outline_text')
    op.drop_column('proposal', 'requirements_html')
    op.drop_column('proposal', 'requirements_text')


def downgrade():
    op.add_column(
        'proposal',
        sa.Column('requirements_text', sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal',
        sa.Column('requirements_html', sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal',
        sa.Column('outline_text', sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal', sa.Column('links', sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'proposal', sa.Column('bio_text', sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'proposal', sa.Column('bio_html', sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'proposal',
        sa.Column('phone', sa.VARCHAR(length=80), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal',
        sa.Column('abstract_text', sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal',
        sa.Column(
            'location',
            sa.VARCHAR(length=80),
            autoincrement=False,
            nullable=False,
            server_default='',
        ),
    )
    op.alter_column('proposal', 'location', server_default=None)
    op.add_column(
        'proposal',
        sa.Column('email_address_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal',
        sa.Column('abstract_html', sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal', sa.Column('slides', sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'proposal',
        sa.Column('outline_html', sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'proposal_email_address_id_fkey',
        'proposal',
        'email_address',
        ['email_address_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_proposal_email_address_id', 'proposal', ['email_address_id'], unique=False
    )
