"""Complement email md5sum with blake2b.

Revision ID: 047ebdac558b
Revises: f58bd7c54f9b
Create Date: 2020-06-05 04:10:56.627503

"""

import hashlib

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

# revision identifiers, used by Alembic.
revision = '047ebdac558b'
down_revision = 'f58bd7c54f9b'
branch_labels = None
depends_on = None


user_email = table(
    'user_email',
    column('id', sa.Integer),
    column('email', sa.Unicode),
    column('md5sum', sa.Unicode),
    column('blake2b', sa.LargeBinary),
)

user_email_claim = table(
    'user_email_claim',
    column('id', sa.Integer),
    column('email', sa.Unicode),
    column('md5sum', sa.Unicode),
    column('blake2b', sa.LargeBinary),
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
    conn = op.get_bind()

    # Add blake2b column to UserEmail
    op.add_column('user_email', sa.Column('blake2b', sa.LargeBinary(), nullable=True))
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_email))
    progress = get_progressbar("Emails", count)
    progress.start()
    items = conn.execute(sa.select([user_email.c.id, user_email.c.email]))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(user_email)
            .where(user_email.c.id == item.id)
            .values(
                md5sum=hashlib.md5(item.email.lower().encode()).hexdigest(),  # nosec
                blake2b=hashlib.blake2b(
                    item.email.lower().encode(), digest_size=16
                ).digest(),
            )
        )
        progress.update(counter)
    progress.finish()
    op.create_unique_constraint('user_email_blake2b_key', 'user_email', ['blake2b'])
    op.alter_column('user_email', 'blake2b', nullable=False)

    # Add blake2b column to UserEmailClaim
    op.add_column(
        'user_email_claim', sa.Column('blake2b', sa.LargeBinary(), nullable=True)
    )
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_email_claim))
    progress = get_progressbar("Email claims", count)
    progress.start()
    items = conn.execute(sa.select([user_email_claim.c.id, user_email_claim.c.email]))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(user_email_claim)
            .where(user_email_claim.c.id == item.id)
            .values(
                md5sum=hashlib.md5(item.email.lower().encode()).hexdigest(),  # nosec
                blake2b=hashlib.blake2b(
                    item.email.lower().encode(), digest_size=16
                ).digest(),
            )
        )
        progress.update(counter)
    progress.finish()
    op.create_index('ix_user_email_claim_blake2b', 'user_email_claim', ['blake2b'])
    op.alter_column('user_email_claim', 'blake2b', nullable=False)

    # Remove column length requirement on User.pw_hash
    op.alter_column('user', 'pw_hash', existing_type=sa.Unicode(80), type_=sa.Unicode)


def downgrade():
    op.alter_column('user', 'pw_hash', existing_type=sa.Unicode, type_=sa.Unicode(80))
    op.drop_index('ix_user_email_claim_blake2b', 'user_email_claim')
    op.drop_column('user_email_claim', 'blake2b')
    op.drop_constraint('user_email_blake2b_key', 'user_email', type_='unique')
    op.drop_column('user_email', 'blake2b')
