"""Remove team fkeys.

Revision ID: 7ee3c83f713f
Revises: 71fcac85957c
Create Date: 2020-04-28 02:24:31.889951

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7ee3c83f713f'
down_revision = '71fcac85957c'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.drop_constraint(
        'organization_owners_id_fkey', 'organization', type_='foreignkey'
    )
    op.drop_column('organization', 'owners_id')
    op.drop_constraint('profile_admin_team_id_fkey', 'profile', type_='foreignkey')
    op.drop_column('profile', 'admin_team_id')
    op.drop_constraint('project_checkin_team_id_fkey', 'project', type_='foreignkey')
    op.drop_constraint('project_admin_team_id_fkey', 'project', type_='foreignkey')
    op.drop_constraint('project_review_team_id_fkey', 'project', type_='foreignkey')
    op.drop_column('project', 'admin_team_id')
    op.drop_column('project', 'review_team_id')
    op.drop_column('project', 'checkin_team_id')


def downgrade() -> None:
    op.add_column(
        'project',
        sa.Column('checkin_team_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'project',
        sa.Column('review_team_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'project',
        sa.Column('admin_team_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'project_review_team_id_fkey',
        'project',
        'team',
        ['review_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'project_admin_team_id_fkey',
        'project',
        'team',
        ['admin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'project_checkin_team_id_fkey',
        'project',
        'team',
        ['checkin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'profile',
        sa.Column('admin_team_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'profile_admin_team_id_fkey',
        'profile',
        'team',
        ['admin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'organization',
        sa.Column('owners_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'organization_owners_id_fkey', 'organization', 'team', ['owners_id'], ['id']
    )
