# type: ignore
"""Drop old user and team tables.

Revision ID: d50c3d8e3f33
Revises: 62d770006955
Create Date: 2020-04-07 05:17:03.917173

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd50c3d8e3f33'
down_revision = '62d770006955'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade():
    op.drop_table('old_users_teams')
    op.drop_table('old_user')
    op.drop_index('ix_old_team_org_uuid', table_name='old_team')
    op.drop_table('old_team')


def downgrade():
    op.create_table(
        'old_team',
        sa.Column(
            'id',
            sa.INTEGER(),
            server_default=sa.text("nextval('old_team_id_seq'::regclass)"),
            autoincrement=True,
            nullable=False,
        ),
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
        sa.Column('title', sa.VARCHAR(length=250), autoincrement=False, nullable=False),
        sa.Column('owners', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('uuid', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column('org_uuid', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='old_team_pkey'),
        sa.UniqueConstraint('uuid', name='old_team_uuid_key'),
        postgresql_ignore_search_path=False,
    )
    op.create_index('ix_old_team_org_uuid', 'old_team', ['org_uuid'], unique=False)
    op.create_table(
        'old_user',
        sa.Column(
            'id',
            sa.INTEGER(),
            server_default=sa.text("nextval('old_user_id_seq'::regclass)"),
            autoincrement=True,
            nullable=False,
        ),
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
        sa.Column(
            'username', sa.VARCHAR(length=80), autoincrement=False, nullable=True
        ),
        sa.Column(
            'lastuser_token_scope',
            sa.VARCHAR(length=250),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            'lastuser_token_type',
            sa.VARCHAR(length=250),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            'lastuser_token', sa.VARCHAR(length=22), autoincrement=False, nullable=True
        ),
        sa.Column(
            'fullname', sa.VARCHAR(length=80), autoincrement=False, nullable=False
        ),
        sa.Column('email', sa.VARCHAR(length=80), autoincrement=False, nullable=True),
        sa.Column(
            'userinfo',
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column('status', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('uuid', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='old_user_pkey'),
        sa.UniqueConstraint('email', name='old_user_email_key'),
        sa.UniqueConstraint('lastuser_token', name='old_user_lastuser_token_key'),
        sa.UniqueConstraint('username', name='old_user_username_key'),
        sa.UniqueConstraint('uuid', name='old_user_uuid_key'),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        'old_users_teams',
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
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('old_team_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ['old_team_id'], ['old_team.id'], name='old_users_teams_old_team_id_fkey'
        ),
        sa.ForeignKeyConstraint(
            ['old_user_id'], ['old_user.id'], name='old_users_teams_old_user_id_fkey'
        ),
        sa.PrimaryKeyConstraint(
            'old_user_id', 'old_team_id', name='old_users_teams_pkey'
        ),
    )
