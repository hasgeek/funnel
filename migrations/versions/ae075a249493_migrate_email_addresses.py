"""Migrate email addresses.

Revision ID: ae075a249493
Revises: 9333436765cd
Create Date: 2020-06-11 08:01:40.108228

"""

import hashlib

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import idna
import progressbar.widgets

# revision identifiers, used by Alembic.
revision = 'ae075a249493'
down_revision = '9333436765cd'
branch_labels = None
depends_on = None


# --- Tables ---------------------------------------------------------------------------


user_email = table(
    'user_email',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('email', sa.Unicode),
    column('domain', sa.Unicode),
    column('md5sum', sa.Unicode),
    column('blake2b', sa.LargeBinary),
    column('email_address_id', sa.Integer),
)

user_email_claim = table(
    'user_email_claim',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('email', sa.Unicode),
    column('domain', sa.Unicode),
    column('md5sum', sa.Unicode),
    column('blake2b', sa.LargeBinary),
    column('email_address_id', sa.Integer),
)


proposal = table(
    'proposal',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
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


def email_blake2b128_hash(email):
    # This does not perform IDNA encoding as the original code that used 128-bit hashes
    # did not process IDNA encoding either
    return hashlib.blake2b(email.lower().encode('utf-8'), digest_size=16).digest()


def email_md5sum(email):
    # This does not perform IDNA encoding as the original code that used 128-bit hashes
    # did not process IDNA encoding either
    return hashlib.md5(email.lower().encode('utf-8')).hexdigest()  # nosec


def email_domain(email):
    return idna.encode(email.split('@', 1)[1], uts46=True).decode()


def email_domain_naive(email):
    return email.lower().split('@', 1)[1]


# --- Migrations -----------------------------------------------------------------------


def upgrade():
    conn = op.get_bind()

    # --- UserEmail --------------------------------------------------------------------
    op.add_column(
        'user_email', sa.Column('email_address_id', sa.Integer(), nullable=True)
    )

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_email))
    progress = get_progressbar("Emails", count)
    progress.start()
    items = conn.execute(
        sa.select(
            [
                user_email.c.id,
                user_email.c.email,
                user_email.c.created_at,
                user_email.c.updated_at,
            ]
        ).order_by(user_email.c.id)
    )
    for counter, item in enumerate(items):
        blake2b160 = email_blake2b160_hash(item.email)
        existing = conn.execute(
            sa.select([email_address.c.id, email_address.c.created_at])
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
        else:
            ea_id = conn.execute(
                email_address.insert()
                .values(
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    email=item.email,
                    domain=email_domain(item.email),
                    blake2b160=blake2b160,
                    blake2b160_canonical=email_blake2b160_hash(
                        canonical_email_representation(item.email)[0]
                    ),
                    delivery_state=0,
                    delivery_state_at=item.updated_at,
                    is_blocked=False,
                )
                .returning(email_address.c.id)
            ).fetchone()[0]

        conn.execute(
            user_email.update()
            .where(user_email.c.id == item.id)
            .values(email_address_id=ea_id)
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('user_email', 'email_address_id', nullable=False)
    op.drop_index('ix_user_email_domain', table_name='user_email')
    op.drop_constraint('user_email_blake2b_key', 'user_email', type_='unique')
    op.drop_constraint('user_email_email_key', 'user_email', type_='unique')
    op.drop_constraint('user_email_md5sum_key', 'user_email', type_='unique')
    op.create_unique_constraint(
        'user_email_email_address_id_key', 'user_email', ['email_address_id']
    )
    op.create_foreign_key(
        'user_email_email_address_id_fkey',
        'user_email',
        'email_address',
        ['email_address_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.drop_column('user_email', 'blake2b')
    op.drop_column('user_email', 'email')
    op.drop_column('user_email', 'domain')
    op.drop_column('user_email', 'md5sum')

    # --- UserEmailClaim ---------------------------------------------------------------
    op.add_column(
        'user_email_claim', sa.Column('email_address_id', sa.Integer(), nullable=True)
    )
    op.create_unique_constraint(
        'user_email_claim_user_id_email_address_id_key',
        'user_email_claim',
        ['user_id', 'email_address_id'],
    )
    op.create_foreign_key(
        'user_email_claim_email_address_id_fkey',
        'user_email_claim',
        'email_address',
        ['email_address_id'],
        ['id'],
        ondelete='SET NULL',
    )

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_email_claim))
    progress = get_progressbar("Email claims", count)
    progress.start()
    items = conn.execute(
        sa.select(
            [
                user_email_claim.c.id,
                user_email_claim.c.email,
                user_email_claim.c.created_at,
                user_email_claim.c.updated_at,
            ]
        ).order_by(user_email_claim.c.id)
    )
    for counter, item in enumerate(items):
        blake2b160 = email_blake2b160_hash(item.email)
        existing = conn.execute(
            sa.select([email_address.c.id, email_address.c.created_at])
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
        else:
            ea_id = conn.execute(
                email_address.insert()
                .values(
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    email=item.email,
                    domain=email_domain(item.email),
                    blake2b160=blake2b160,
                    blake2b160_canonical=email_blake2b160_hash(
                        canonical_email_representation(item.email)[0]
                    ),
                    delivery_state=0,
                    delivery_state_at=item.updated_at,
                    is_blocked=False,
                )
                .returning(email_address.c.id)
            ).fetchone()[0]
        conn.execute(
            user_email_claim.update()
            .where(user_email_claim.c.id == item.id)
            .values(email_address_id=ea_id)
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('user_email_claim', 'email_address_id', nullable=False)
    op.create_index(
        op.f('ix_user_email_claim_email_address_id'),
        'user_email_claim',
        ['email_address_id'],
        unique=False,
    )
    op.drop_index('ix_user_email_claim_domain', table_name='user_email_claim')
    op.drop_index('ix_user_email_claim_email', table_name='user_email_claim')
    op.drop_index('ix_user_email_claim_md5sum', table_name='user_email_claim')
    op.drop_constraint(
        'user_email_claim_user_id_email_key', 'user_email_claim', type_='unique'
    )
    op.drop_column('user_email_claim', 'email')
    op.drop_column('user_email_claim', 'domain')
    op.drop_column('user_email_claim', 'md5sum')

    # --- Proposal ---------------------------------------------------------------------
    op.add_column(
        'proposal', sa.Column('email_address_id', sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f('ix_proposal_email_address_id'),
        'proposal',
        ['email_address_id'],
        unique=False,
    )
    op.create_foreign_key(
        'proposal_email_address_id_fkey',
        'proposal',
        'email_address',
        ['email_address_id'],
        ['id'],
        ondelete='SET NULL',
    )

    count = conn.scalar(
        sa.select([sa.func.count('*')])
        .select_from(proposal)
        .where(proposal.c.email.isnot(None))
    )
    progress = get_progressbar("Proposals", count)
    progress.start()
    items = conn.execute(
        sa.select([proposal.c.id, proposal.c.email, proposal.c.created_at])
        .where(proposal.c.email.isnot(None))
        .order_by(proposal.c.id)
    )
    for counter, item in enumerate(items):
        blake2b160 = email_blake2b160_hash(item.email)
        existing = conn.execute(
            sa.select([email_address.c.id, email_address.c.created_at])
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
        else:
            ea_id = conn.execute(
                email_address.insert()
                .values(
                    created_at=item.created_at,
                    updated_at=item.created_at,
                    email=item.email,
                    domain=email_domain(item.email),
                    blake2b160=blake2b160,
                    blake2b160_canonical=email_blake2b160_hash(
                        canonical_email_representation(item.email)[0]
                    ),
                    delivery_state=0,
                    delivery_state_at=item.created_at,
                    is_blocked=False,
                )
                .returning(email_address.c.id)
            ).fetchone()[0]
        conn.execute(
            proposal.update()
            .where(proposal.c.id == item.id)
            .values(email_address_id=ea_id)
        )
        progress.update(counter)
    progress.finish()

    op.drop_column('proposal', 'email')


def downgrade():
    conn = op.get_bind()

    # --- Proposal ---------------------------------------------------------------------
    op.add_column(
        'proposal',
        sa.Column('email', sa.VARCHAR(length=80), autoincrement=False, nullable=True),
    )

    count = conn.scalar(
        sa.select([sa.func.count('*')])
        .select_from(proposal)
        .where(proposal.c.email_address_id.isnot(None))
    )
    progress = get_progressbar("Proposals", count)
    progress.start()
    items = conn.execute(
        sa.select([proposal.c.id, email_address.c.email]).where(
            proposal.c.email_address_id == email_address.c.id
        )
    )
    for counter, item in enumerate(items):
        conn.execute(
            proposal.update().where(proposal.c.id == item.id).values(email=item.email)
        )
        progress.update(counter)
    progress.finish()

    op.drop_constraint('proposal_email_address_id_fkey', 'proposal', type_='foreignkey')
    op.drop_index(op.f('ix_proposal_email_address_id'), table_name='proposal')
    op.drop_column('proposal', 'email_address_id')

    # --- UserEmailClaim ---------------------------------------------------------------
    op.add_column(
        'user_email_claim',
        sa.Column('md5sum', sa.VARCHAR(length=32), autoincrement=False, nullable=True),
    )
    op.add_column(
        'user_email_claim',
        sa.Column('domain', sa.VARCHAR(length=253), autoincrement=False, nullable=True),
    )
    op.add_column(
        'user_email_claim',
        sa.Column('email', sa.VARCHAR(length=254), autoincrement=False, nullable=True),
    )

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
                email=item.email,
                md5sum=email_md5sum(item.email),
                domain=email_domain(item.email),
            )
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('user_email_claim', 'md5sum', nullable=False)
    op.alter_column('user_email_claim', 'domain', nullable=False)

    # Due to a longstanding oversight, UserEmailClaim.email was nullable. We do not
    # attempt to correct it in this migration

    op.drop_constraint(
        'user_email_claim_email_address_id_fkey', 'user_email_claim', type_='foreignkey'
    )
    op.drop_constraint(
        'user_email_claim_user_id_email_address_id_key',
        'user_email_claim',
        type_='unique',
    )
    op.create_unique_constraint(
        'user_email_claim_user_id_email_key', 'user_email_claim', ['user_id', 'email']
    )
    op.create_index(
        'ix_user_email_claim_md5sum', 'user_email_claim', ['md5sum'], unique=False
    )
    op.create_index(
        'ix_user_email_claim_email', 'user_email_claim', ['email'], unique=False
    )
    op.create_index(
        'ix_user_email_claim_domain', 'user_email_claim', ['domain'], unique=False
    )
    op.drop_index(
        op.f('ix_user_email_claim_email_address_id'), table_name='user_email_claim'
    )
    op.drop_column('user_email_claim', 'email_address_id')

    # --- UserEmail --------------------------------------------------------------------
    op.add_column(
        'user_email',
        sa.Column('md5sum', sa.VARCHAR(length=32), autoincrement=False, nullable=True),
    )
    op.add_column(
        'user_email',
        sa.Column('domain', sa.VARCHAR(length=253), autoincrement=False, nullable=True),
    )
    op.add_column(
        'user_email',
        sa.Column('email', sa.VARCHAR(length=254), autoincrement=False, nullable=True),
    )
    op.add_column(
        'user_email',
        sa.Column('blake2b', postgresql.BYTEA(), autoincrement=False, nullable=True),
    )

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_email))
    progress = get_progressbar("Emails", count)
    progress.start()
    items = conn.execute(
        sa.select([user_email.c.id, email_address.c.email]).where(
            user_email.c.email_address_id == email_address.c.id
        )
    )
    for counter, item in enumerate(items):
        conn.execute(
            user_email.update()
            .where(user_email.c.id == item.id)
            .values(
                email=item.email,
                md5sum=email_md5sum(item.email),
                domain=email_domain(item.email),
                blake2b=email_blake2b128_hash(item.email),
            )
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('user_email', 'md5sum', nullable=False)
    op.alter_column('user_email', 'domain', nullable=False)
    op.alter_column('user_email', 'email', nullable=False)
    op.alter_column('user_email', 'blake2b', nullable=False)

    op.drop_constraint(
        'user_email_email_address_id_fkey', 'user_email', type_='foreignkey'
    )
    op.drop_constraint('user_email_email_address_id_key', 'user_email', type_='unique')
    op.create_unique_constraint('user_email_md5sum_key', 'user_email', ['md5sum'])
    op.create_unique_constraint('user_email_email_key', 'user_email', ['email'])
    op.create_unique_constraint('user_email_blake2b_key', 'user_email', ['blake2b'])
    op.create_index('ix_user_email_domain', 'user_email', ['domain'], unique=False)
    op.drop_column('user_email', 'email_address_id')

    # --- Drop imported contents and restart sequence ----------------------------------
    op.execute(email_address.delete())
    op.execute(sa.text('ALTER SEQUENCE email_address_id_seq RESTART'))
