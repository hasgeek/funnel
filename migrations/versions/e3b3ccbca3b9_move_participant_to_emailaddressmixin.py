# type: ignore
"""Move Participant to EmailAddressMixin.

Revision ID: e3b3ccbca3b9
Revises: ae075a249493
Create Date: 2020-06-17 02:13:45.493791

"""

from typing import Optional, Tuple, Union
import hashlib

from alembic import op
from progressbar import ProgressBar
from pyisemail import is_email
from sqlalchemy.sql import column, table
import idna
import progressbar.widgets
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e3b3ccbca3b9'
down_revision = 'ae075a249493'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


# --- Tables ---------------------------------------------------------------------------

user = table('user', column('id', sa.Integer))

user_email = table(
    'user_email',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('email_address_id', sa.Integer),
    column('user_id', sa.Integer),
)

participant = table(
    'participant',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('user_id', sa.Integer),
    column('project_id', sa.Integer),
    column('email', sa.Unicode),
    column('email_address_id', sa.Integer),
)

email_address = table(
    'email_address',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('email', sa.Unicode),
    column('domain', sa.Unicode),
    column('blake2b160', sa.LargeBinary),
    column('blake2b160_canonical', sa.LargeBinary),
    column('delivery_state', sa.Integer),
    column('delivery_state_at', sa.TIMESTAMP(timezone=True)),
    column('is_blocked', sa.Boolean),
)

# --- Functions ------------------------------------------------------------------------


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


# These are copied from models/email_address.py:


def canonical_email_representation(email):
    if '@' not in email:
        raise ValueError("Not an email address")
    mailbox, domain = email.split('@', 1)
    mailbox = mailbox.lower()
    if '+' in mailbox:
        mailbox = mailbox[: mailbox.find('+')]

    representations = [f'{mailbox}@{domain}']

    # Hardcode for Gmail's special cases owing to its popularity
    if domain == 'googlemail.com':
        domain = 'gmail.com'
    if domain == 'gmail.com':
        if '.' in mailbox:
            mailbox = mailbox.replace('.', '')
        gmail_representation = f'{mailbox}@{domain}'
        if gmail_representation != representations[0]:
            # Gmail special case should take priority
            representations.insert(0, gmail_representation)

    return representations


def email_normalized(email):
    mailbox, domain = email.split('@', 1)
    mailbox = mailbox.lower()
    domain = idna.encode(domain, uts46=True).decode()
    return f'{mailbox}@{domain}'


def email_blake2b160_hash(email):
    return hashlib.blake2b(
        email_normalized(email).encode('utf-8'), digest_size=20
    ).digest()


def email_domain(email):
    return idna.encode(email.split('@', 1)[1], uts46=True).decode()


def upgrade():
    conn = op.get_bind()

    op.add_column(
        'participant', sa.Column('email_address_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'participant_email_address_id_fkey',
        'participant',
        'email_address',
        ['email_address_id'],
        ['id'],
        ondelete='SET NULL',
    )

    count = conn.scalar(sa.select(sa.func.count('*')).select_from(participant))
    progress = get_progressbar("Participants", count)
    progress.start()
    items = conn.execute(
        sa.select(
            participant.c.id,
            participant.c.project_id,
            participant.c.email,
            participant.c.created_at,
        ).order_by(participant.c.id)
    )
    dupe_counter = {}  # (project_id, blake2b160): counter
    for counter, item in enumerate(items):
        email = item.email.strip()
        if not is_email(email, check_dns=False, diagnose=False):
            email = 'invalid@example.org'

        blake2b160 = email_blake2b160_hash(email)

        dc_key = (item.project_id, blake2b160)
        dc_count = dupe_counter.get(dc_key, 0)
        dupe_counter[dc_key] = dc_count + 1
        # If we've seen this pairing of project_id and hash already, add a counter
        if dc_count > 0:
            mailbox, domain = email.split('@', 1)
            email = f'{mailbox}+{dc_count}@{domain}'  # Will start counter at +1
            blake2b160 = email_blake2b160_hash(email)

        existing = conn.execute(
            sa.select(email_address.c.id, email_address.c.created_at)
            .where(email_address.c.blake2b160 == blake2b160)
            .limit(1)
        ).fetchone()
        if existing:
            ea_id = existing.id
            if existing.created_at > item.created_at:
                conn.execute(
                    email_address.update()
                    .where(email_address.c.id == existing.id)
                    .values(created_at=item.created_at)
                )
            # Get linked user via user_email if present
            user_id = conn.scalar(
                sa.select(user.c.id).where(
                    sa.and_(
                        email_address.c.id == ea_id,
                        user_email.c.email_address_id == email_address.c.id,
                        user.c.id == user_email.c.user_id,
                    )
                )
            )
        else:
            ea_id = conn.scalar(
                email_address.insert()
                .values(
                    created_at=item.created_at,
                    updated_at=item.created_at,
                    email=email,
                    domain=email_domain(email),
                    blake2b160=blake2b160,
                    blake2b160_canonical=email_blake2b160_hash(
                        canonical_email_representation(email)[0]
                    ),
                    delivery_state=0,
                    delivery_state_at=item.created_at,
                    is_blocked=False,
                )
                .returning(email_address.c.id)
            )
            # New email address, so there won't be a linked user_email record
            user_id = None
        conn.execute(
            participant.update()
            .where(participant.c.id == item.id)
            .values(email_address_id=ea_id, user_id=user_id)
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('participant', 'email_address_id', nullable=False)

    op.create_index(
        op.f('ix_participant_email_address_id'),
        'participant',
        ['email_address_id'],
        unique=False,
    )
    op.create_unique_constraint(
        'participant_project_id_email_address_id_key',
        'participant',
        ['project_id', 'email_address_id'],
    )
    op.drop_constraint(
        'participant_project_id_email_key', 'participant', type_='unique'
    )
    op.drop_column('participant', 'email')


def downgrade():
    conn = op.get_bind()

    op.add_column(
        'participant',
        sa.Column('email', sa.VARCHAR(length=254), autoincrement=False, nullable=True),
    )
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(participant))
    progress = get_progressbar("Participants", count)
    progress.start()
    items = conn.execute(
        sa.select(participant.c.id, email_address.c.email).where(
            participant.c.email_address_id == email_address.c.id
        )
    )
    for counter, item in enumerate(items):
        conn.execute(
            participant.update()
            .where(participant.c.id == item.id)
            .values(email=item.email, user_id=None)
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('participant', 'email', nullable=False)
    op.create_unique_constraint(
        'participant_project_id_email_key', 'participant', ['project_id', 'email']
    )
    op.drop_constraint(
        'participant_email_address_id_fkey', 'participant', type_='foreignkey'
    )
    op.drop_index(op.f('ix_participant_email_address_id'), table_name='participant')
    op.drop_column('participant', 'email_address_id')
