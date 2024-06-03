"""Add migrated membership record type.

Revision ID: 20f830d2fead
Revises: 9ada98ef2f2d
Create Date: 2024-03-27 21:03:12.522442

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20f830d2fead'
down_revision: str = '9ada98ef2f2d'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

constraint_renames = {
    'project_membership': [
        (
            'project_crew_membership_has_role',
            'project_membership_has_role',
        ),
        (
            'project_crew_membership_label_check',
            'project_membership_label_check',
        ),
        (
            'project_crew_membership_record_type_check',
            'project_membership_record_type_check',
        ),
        (
            'project_crew_membership_granted_by_id_fkey',
            'project_membership_granted_by_id_fkey',
        ),
        (
            'project_crew_membership_project_id_fkey',
            'project_membership_project_id_fkey',
        ),
        (
            'project_crew_membership_revoked_by_id_fkey',
            'project_membership_revoked_by_id_fkey',
        ),
    ]
}
table_names = [
    'account_membership',
    'commentset_membership',
    'project_membership',
    'project_sponsor_membership',
    'proposal_membership',
    'proposal_sponsor_membership',
    'site_membership',
]


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    for table, renames in constraint_renames.items():
        for old_name, new_name in renames:
            op.execute(
                sa.text(
                    f'ALTER TABLE {table} RENAME CONSTRAINT {old_name} TO {new_name}'
                )
            )
    for table in table_names:
        op.drop_constraint(f'{table}_record_type_check', table, type_='check')
        op.create_check_constraint(
            f'{table}_record_type_check',
            table,
            sa.text('record_type = ANY (ARRAY[1, 2, 3, 4, 5])'),
        )


def downgrade_() -> None:
    """Downgrade default database."""
    for table in table_names:
        op.drop_constraint(f'{table}_record_type_check', table, type_='check')
        op.create_check_constraint(
            f'{table}_record_type_check',
            table,
            sa.text('record_type = ANY (ARRAY[1, 2, 3, 4])'),
        )
    for table, renames in constraint_renames.items():
        for old_name, new_name in renames:
            op.execute(
                sa.text(
                    f'ALTER TABLE {table} RENAME CONSTRAINT {new_name} TO {old_name}'
                )
            )
