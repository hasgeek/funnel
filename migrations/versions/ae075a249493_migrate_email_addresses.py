"""Migrate email addresses

Revision ID: ae075a249493
Revises: 9333436765cd
Create Date: 2020-06-11 08:01:40.108228

"""

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

# revision identifiers, used by Alembic.
revision = 'ae075a249493'
down_revision = '9333436765cd'
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
    # --- UserEmail --------------------------------------------------------------------
    op.add_column(
        'user_email', sa.Column('email_address_id', sa.Integer(), nullable=True)
    )
    # TODO: Migrate
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
    # Migrate
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
    # TODO: Migrate contents
    op.drop_column('proposal', 'email')


def downgrade():
    # --- Proposal ---------------------------------------------------------------------
    op.add_column(
        'proposal',
        sa.Column('email', sa.VARCHAR(length=80), autoincrement=False, nullable=True),
    )
    # TODO: Migrate
    op.drop_constraint('proposal_email_address_id_fkey', 'proposal', type_='foreignkey')
    op.drop_index(op.f('ix_proposal_email_address_id'), table_name='proposal')
    op.drop_column('proposal', 'email_address_id')

    # --- UserEmailClaim ---------------------------------------------------------------
    op.add_column(
        'user_email_claim',
        sa.Column('md5sum', sa.VARCHAR(length=32), autoincrement=False, nullable=False),
    )
    op.add_column(
        'user_email_claim',
        sa.Column(
            'domain', sa.VARCHAR(length=253), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        'user_email_claim',
        sa.Column('email', sa.VARCHAR(length=254), autoincrement=False, nullable=True),
    )
    # TODO: Migrate
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
        sa.Column('md5sum', sa.VARCHAR(length=32), autoincrement=False, nullable=False),
    )
    op.add_column(
        'user_email',
        sa.Column(
            'domain', sa.VARCHAR(length=253), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        'user_email',
        sa.Column('email', sa.VARCHAR(length=254), autoincrement=False, nullable=False),
    )
    op.add_column(
        'user_email',
        sa.Column('blake2b', postgresql.BYTEA(), autoincrement=False, nullable=False),
    )
    # TODO: Migrate
    op.drop_constraint(
        'user_email_email_address_id_fkey', 'user_email', type_='foreignkey'
    )
    op.drop_constraint('user_email_email_address_id_key', 'user_email', type_='unique')
    op.create_unique_constraint('user_email_md5sum_key', 'user_email', ['md5sum'])
    op.create_unique_constraint('user_email_email_key', 'user_email', ['email'])
    op.create_unique_constraint('user_email_blake2b_key', 'user_email', ['blake2b'])
    op.create_index('ix_user_email_domain', 'user_email', ['domain'], unique=False)
    op.drop_column('user_email', 'email_address_id')
