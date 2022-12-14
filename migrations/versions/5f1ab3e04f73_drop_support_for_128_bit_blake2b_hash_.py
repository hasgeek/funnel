"""Drop support for 128-bit blake2b hash in email.

Revision ID: 5f1ab3e04f73
Revises: 3847982f1472
Create Date: 2020-10-07 10:24:32.491617

"""

from typing import Optional, Tuple, Union
import hashlib

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

# revision identifiers, used by Alembic.
revision = '5f1ab3e04f73'
down_revision = '3847982f1472'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

user_email_claim = table(
    'user_email_claim',
    column('id', sa.Integer),
    column('email_address_id', sa.Integer),
    column('blake2b', sa.LargeBinary),
)

email_address = table(
    'email_address',
    column('id', sa.Integer),
    column('email', sa.Unicode),
)


def get_progressbar(label, maxval):
    return ProgressBar(
        maxval=maxval,
        widgets=[
            label,
            ': ',
            progressbar.widgets.Percentage(),
            ' ',
            progressbar.widgets.Bar(),
            ' ',
            progressbar.widgets.ETA(),
            ' ',
        ],
    )


def upgrade():
    op.drop_index('ix_user_email_claim_blake2b', table_name='user_email_claim')
    op.drop_column('user_email_claim', 'blake2b')


def downgrade():
    conn = op.get_bind()
    op.add_column(
        'user_email_claim',
        sa.Column('blake2b', postgresql.BYTEA(), autoincrement=False, nullable=True),
    )
    # Recalculate blake2b hashes
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_email_claim))
    progress = get_progressbar("Email claims", count)
    progress.start()
    items = conn.execute(
        sa.select([user_email_claim.c.id, email_address.c.email]).where(
            user_email_claim.c.email_address_id == email_address.c.id
        )
    )
    for counter, item in enumerate(items):
        conn.execute(
            user_email_claim.update()
            .where(user_email_claim.c.id == item.id)
            .values(
                blake2b=hashlib.blake2b(
                    item.email.lower().encode('utf-8'), digest_size=16
                ).digest(),
            )
        )
        progress.update(counter)
    progress.finish()
    op.alter_column('user_email_claim', 'blake2b', nullable=False)
    op.create_index(
        'ix_user_email_claim_blake2b', 'user_email_claim', ['blake2b'], unique=False
    )
