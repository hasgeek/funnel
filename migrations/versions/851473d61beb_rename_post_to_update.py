"""Rename Post to Update.

Revision ID: 851473d61beb
Revises: dcd0870c24cc
Create Date: 2020-08-08 07:31:11.811599

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '851473d61beb'
down_revision = 'dcd0870c24cc'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

# (old, new)
renamed_constraints = [
    ('post_pkey', 'update_pkey'),
    ('post_uuid_key', 'update_uuid_key'),
]

# (old, new)
renamed_indexes = [
    ('ix_post_deleted_by_id', 'ix_update_deleted_by_id'),
    ('ix_post_project_id', 'ix_update_project_id'),
    ('ix_post_published_by_id', 'ix_update_published_by_id'),
    ('ix_post_state', 'ix_update_state'),
    ('ix_post_user_id', 'ix_update_user_id'),
    ('ix_post_visibility_state', 'ix_update_visibility_state'),
]


def upgrade() -> None:
    op.drop_index('ix_post_profile_id', 'post')
    op.drop_constraint('post_owner_check', 'post', type_='check')
    op.drop_column('post', 'profile_id')
    op.rename_table('post', 'update')
    op.execute(sa.DDL('ALTER SEQUENCE post_id_seq RENAME TO update_id_seq'))

    for old, new in renamed_constraints:
        op.execute(sa.DDL(f'ALTER TABLE update RENAME CONSTRAINT "{old}" TO "{new}"'))

    for old, new in renamed_indexes:
        op.execute(sa.DDL(f'ALTER INDEX "{old}" RENAME TO "{new}"'))


def downgrade() -> None:
    for old, new in renamed_indexes:
        op.execute(sa.DDL(f'ALTER INDEX "{new}" RENAME TO "{old}"'))

    for old, new in renamed_constraints:
        op.execute(sa.DDL(f'ALTER TABLE update RENAME CONSTRAINT "{new}" TO "{old}"'))

    op.execute(sa.DDL('ALTER SEQUENCE update_id_seq RENAME TO post_id_seq'))
    op.rename_table('update', 'post')
    op.add_column(
        'post',
        sa.Column(
            'profile_id', sa.Integer(), sa.ForeignKey('profile.id'), nullable=True
        ),
    )
    op.create_index('ix_post_profile_id', 'post', ['profile_id'], unique=False)
    op.create_check_constraint(
        'post_owner_check',
        'post',
        '(\nCASE\n    WHEN (profile_id IS NOT NULL) THEN 1\n    ELSE 0\nEND +\nCASE\n    WHEN (project_id IS NOT NULL) THEN 1\n    ELSE 0\nEND) = 1',
    )
