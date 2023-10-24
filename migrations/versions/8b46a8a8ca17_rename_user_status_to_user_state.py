"""Rename user.status to user.state.

Revision ID: 8b46a8a8ca17
Revises: 5f1ab3e04f73
Create Date: 2020-11-05 11:01:13.504106

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '8b46a8a8ca17'
down_revision = '5f1ab3e04f73'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

USER_STATES = {
    0: "Active",
    1: "Suspended",
    2: "Merged",
    3: "Invited",
    4: "Deleted",
}


def upgrade() -> None:
    op.alter_column('user', 'status', new_column_name='state')
    op.create_check_constraint(
        'user_state_check',
        'user',
        sa.sql.column('state').in_(sorted(USER_STATES.keys())),
    )


def downgrade() -> None:
    op.drop_constraint('user_state_check', 'user', type_='check')
    op.alter_column('user', 'state', new_column_name='status')
