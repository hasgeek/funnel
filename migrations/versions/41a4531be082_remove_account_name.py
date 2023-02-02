"""Remove account_name.

Revision ID: 41a4531be082
Revises: e8665a81606d
Create Date: 2020-04-16 20:46:50.889210

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '41a4531be082'
down_revision = 'e8665a81606d'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

account_name = table(
    'account_name',
    column('id', postgresql.UUID()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('name', sa.Unicode(63)),
    column('user_id', sa.Integer),
    column('organization_id', sa.Integer),
    column('reserved', sa.Boolean),
)

profile = table(
    'profile',
    column('uuid', postgresql.UUID()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('name', sa.Unicode(63)),
    column('user_id', sa.Integer),
    column('organization_id', sa.Integer),
    column('reserved', sa.Boolean),
)


def upgrade():
    op.drop_index('ix_account_name_reserved', table_name='account_name')
    op.drop_table('account_name')


def downgrade():
    op.create_table(
        'account_name',
        sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('name', sa.VARCHAR(length=63), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('organization_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('reserved', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.CheckConstraint(
            '((\nCASE\n    WHEN (user_id IS NOT NULL) THEN 1\n    ELSE 0\nEND +\nCASE\n    WHEN (organization_id IS NOT NULL) THEN 1\n    ELSE 0\nEND) +\nCASE\n    WHEN (reserved IS TRUE) THEN 1\n    ELSE 0\nEND) = 1',
            name='account_name_owner_check',
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organization.id'],
            name='account_name_organization_id_fkey',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['user.id'],
            name='account_name_user_id_fkey',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name='account_name_pkey'),
        sa.UniqueConstraint('name', name='account_name_name_key'),
        sa.UniqueConstraint('organization_id', name='account_name_organization_id_key'),
        sa.UniqueConstraint('user_id', name='account_name_user_id_key'),
    )
    op.create_index(
        'ix_account_name_reserved', 'account_name', ['reserved'], unique=False
    )

    op.execute(
        account_name.insert().from_select(
            [
                'id',
                'created_at',
                'updated_at',
                'name',
                'user_id',
                'organization_id',
                'reserved',
            ],
            sa.select(
                profile.c.uuid,
                profile.c.created_at,
                profile.c.updated_at,
                profile.c.name,
                profile.c.user_id,
                profile.c.organization_id,
                profile.c.reserved,
            ),
        )
    )
