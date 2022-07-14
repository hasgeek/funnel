"""Start enums at 1.

Revision ID: 6d031c17a6ee
Revises: a116118d086b
Create Date: 2022-07-13 22:41:32.454251

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision: str = '6d031c17a6ee'
down_revision: str = 'a116118d086b'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


# (table, column, check, values)
table_column_check_values = [
    ('comment_moderator_report', 'report_type', None, (1, 2)),
    ('comment', 'state', 'comment_state_check', (1, 2, 3, 4, 5, 6)),
    (
        'email_address',
        'delivery_state',
        'email_address_delivery_state_check',
        (1, 2, 4, 5),  # No 3 here
    ),
    ('sms_message', 'status', None, (1, 2, 3, 4, 5)),
    ('profile', 'state', 'profile_state_check', (1, 2, 3)),
    ('project', 'state', 'project_state_check', (1, 2, 3, 4)),
    ('project', 'cfp_state', 'project_cfp_state_check', (1, 2, 3)),
    (
        'proposal',
        'state',
        'proposal_state_check',
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
    ),
    ('update', 'state', 'update_state_check', (1, 2, 3)),
    ('update', 'visibility_state', 'update_visibility_state_check', (1, 2)),
    ('user', 'state', 'user_state_check', (1, 2, 3, 4, 5)),
    # Membership classes
    (
        'organization_membership',
        'record_type',
        'organization_membership_record_type_check',
        (1, 2, 3, 4),
    ),
    (
        'project_crew_membership',
        'record_type',
        'project_crew_membership_record_type_check',
        (1, 2, 3, 4),
    ),
    (
        'proposal_membership',
        'record_type',
        'proposal_membership_record_type_check',
        (1, 2, 3, 4),
    ),
    (
        'site_membership',
        'record_type',
        'site_membership_record_type_check',
        (1, 2, 3, 4),
    ),
    (
        'commentset_membership',
        'record_type',
        None,
        (1, 2, 3, 4),
    ),
    (
        'project_sponsor_membership',
        'record_type',
        'project_sponsor_membership_record_type_check',
        (1, 2, 3, 4),
    ),
    (
        'proposal_sponsor_membership',
        'record_type',
        'proposal_sponsor_membership_record_type_check',
        (1, 2, 3, 4),
    ),
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
    """Upgrade database bind ''."""
    for table_name, column_name, check_name, values in table_column_check_values:
        print(f"Upgrading {table_name}.{column_name}")  # noqa: T201
        tstruct = table(table_name, column(column_name))
        if check_name:
            op.drop_constraint(check_name, table_name, type_='check')
        for value in sorted(values, reverse=True):
            op.execute(
                tstruct.update()
                .where(getattr(tstruct.c, column_name) == value - 1)
                .values(**{column_name: value})
            )
        if not check_name:
            check_name = table_name + '_' + column_name + '_check'
        op.create_check_constraint(
            check_name, table_name, column(column_name).in_(values)
        )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    for table_name, column_name, check_name, values in reversed(
        table_column_check_values
    ):
        print(f"Downgrading {table_name}.{column_name}")  # noqa: T201
        tstruct = table(table_name, column(column_name))
        if not check_name:
            mcheck = table_name + '_' + column_name + '_check'
        else:
            mcheck = check_name
        op.drop_constraint(mcheck, table_name, type_='check')
        for value in sorted(values):
            op.execute(
                tstruct.update()
                .where(getattr(tstruct.c, column_name) == value)
                .values(**{column_name: value - 1})
            )
        if check_name:
            op.create_check_constraint(
                check_name, table_name, column(column_name).in_([v - 1 for v in values])
            )
