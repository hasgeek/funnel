"""Add email_address.active_at.

Revision ID: c47007758ee6
Revises: b7fa6df99855
Create Date: 2020-08-20 21:47:43.356619

"""

from alembic import op
from sqlalchemy import column, table
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c47007758ee6'
down_revision = 'b7fa6df99855'
branch_labels = None
depends_on = None


class DELIVERY_STATE:
    SENT = 1
    ACTIVE = 2


email_address = table(
    'email_address',
    column('id', sa.Integer()),
    column('delivery_state', sa.Integer()),
    column('delivery_state_at', sa.TIMESTAMP(timezone=True)),
    column('active_at', sa.TIMESTAMP(timezone=True)),
)


def upgrade():
    op.add_column(
        'email_address',
        sa.Column('active_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(
        email_address.update()
        .where(email_address.c.delivery_state == DELIVERY_STATE.ACTIVE)
        .values(
            {
                'active_at': email_address.c.delivery_state_at,
                'delivery_state': DELIVERY_STATE.SENT,
            }
        )
    )
    op.create_check_constraint(
        'email_address_delivery_state_check',
        'email_address',
        'delivery_state IN (0, 1, 3, 4)',
    )


def downgrade():
    op.drop_constraint(
        'email_address_delivery_state_check', 'email_address', type_='check'
    )
    op.execute(
        email_address.update()
        .where(email_address.c.active_at.isnot(None))
        .values({'delivery_state': DELIVERY_STATE.ACTIVE})
    )
    op.drop_column('email_address', 'active_at')
