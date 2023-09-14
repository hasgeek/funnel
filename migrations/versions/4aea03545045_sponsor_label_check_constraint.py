"""Sponsor label check constraint.

Revision ID: 4aea03545045
Revises: aebd5a9e5af1
Create Date: 2021-04-27 04:47:11.001289

"""

from alembic import op
from sqlalchemy.sql import column

# revision identifiers, used by Alembic.
revision = '4aea03545045'
down_revision = 'aebd5a9e5af1'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        'sponsor_membership_label_check',
        'sponsor_membership',
        column('label') != '',  # type: ignore[arg-type]
    )


def downgrade() -> None:
    op.drop_constraint(
        'sponsor_membership_label_check', 'sponsor_membership', type_='check'
    )
