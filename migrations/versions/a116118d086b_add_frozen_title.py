"""Add frozen title.

Revision ID: a116118d086b
Revises: b7165507d80c
Create Date: 2022-07-13 20:59:11.442605

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a116118d086b'
down_revision: str = 'b7165507d80c'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


# (old, new)
renamed_constraints = [
    ('sponsor_membership_pkey', 'project_sponsor_membership_pkey'),
    ('sponsor_membership_label_check', 'project_sponsor_membership_label_check'),
    (
        'sponsor_membership_record_type_check',
        'project_sponsor_membership_record_type_check',
    ),
    (
        'sponsor_membership_granted_by_id_fkey',
        'project_sponsor_membership_granted_by_id_fkey',
    ),
    (
        'sponsor_membership_profile_id_fkey',
        'project_sponsor_membership_profile_id_fkey',
    ),
    (
        'sponsor_membership_project_id_fkey',
        'project_sponsor_membership_project_id_fkey',
    ),
    (
        'sponsor_membership_revoked_by_id_fkey',
        'project_sponsor_membership_revoked_by_id_fkey',
    ),
]

# (old, new)
renamed_indexes = [
    ('ix_sponsor_membership_active', 'ix_project_sponsor_membership_active'),
    ('ix_sponsor_membership_profile_id', 'ix_project_sponsor_membership_profile_id'),
    ('ix_sponsor_membership_seq', 'ix_project_sponsor_membership_seq'),
]


def upgrade(engine_name='') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name='') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Add optional frozen title."""
    op.rename_table('sponsor_membership', 'project_sponsor_membership')
    for old, new in renamed_constraints:
        op.execute(
            sa.text(
                f'ALTER TABLE project_sponsor_membership RENAME CONSTRAINT'
                f' "{old}" TO "{new}"'
            )
        )
    for old, new in renamed_indexes:
        op.execute(sa.text(f'ALTER INDEX "{old}" RENAME TO "{new}"'))

    op.add_column(
        'proposal_membership', sa.Column('title', sa.Unicode(), nullable=True)
    )
    op.create_check_constraint(
        'proposal_membership_title_check',
        'proposal_membership',
        "title <> ''",
    )
    op.add_column(
        'proposal_sponsor_membership', sa.Column('title', sa.Unicode(), nullable=True)
    )
    op.create_check_constraint(
        'proposal_sponsor_membership_title_check',
        'proposal_sponsor_membership',
        "title <> ''",
    )
    op.add_column(
        'project_sponsor_membership', sa.Column('title', sa.Unicode(), nullable=True)
    )
    op.create_check_constraint(
        'project_sponsor_membership_title_check',
        'project_sponsor_membership',
        "title <> ''",
    )


def downgrade_() -> None:
    """Remove optional frozen title."""
    op.drop_constraint(
        'project_sponsor_membership_title_check', 'project_sponsor_membership'
    )
    op.drop_column('project_sponsor_membership', 'title')
    op.drop_constraint(
        'proposal_sponsor_membership_title_check', 'proposal_sponsor_membership'
    )
    op.drop_column('proposal_sponsor_membership', 'title')
    op.drop_constraint('proposal_membership_title_check', 'proposal_membership')
    op.drop_column('proposal_membership', 'title')

    for old, new in renamed_indexes:
        op.execute(sa.text(f'ALTER INDEX "{new}" RENAME TO "{old}"'))
    for old, new in renamed_constraints:
        op.execute(
            sa.text(
                f'ALTER TABLE project_sponsor_membership RENAME CONSTRAINT'
                f' "{new}" TO "{old}"'
            )
        )
    op.rename_table('project_sponsor_membership', 'sponsor_membership')
