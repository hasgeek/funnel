"""Remove UserGroup model.

Revision ID: 38394aa411d0
Revises: e3bf172763bc
Create Date: 2019-02-28 17:34:53.814507

"""

# revision identifiers, used by Alembic.
revision = '38394aa411d0'
down_revision = 'e3bf172763bc'

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.drop_table('group_members')
    op.drop_table('user_group')


def downgrade() -> None:
    op.create_table(
        'user_group',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            'created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
        sa.Column(
            'updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False
        ),
        sa.Column('project_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=250), autoincrement=False, nullable=False),
        sa.Column('title', sa.VARCHAR(length=250), autoincrement=False, nullable=False),
        sa.CheckConstraint("(name)::text <> ''::text", name='user_group_name_check'),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'], name='user_group_project_id_fkey'
        ),
        sa.PrimaryKeyConstraint('id', name='user_group_pkey'),
        sa.UniqueConstraint(
            'project_id', 'name', name='user_group_project_id_name_key'
        ),
    )
    op.create_table(
        'group_members',
        sa.Column('group_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ['group_id'], ['user_group.id'], name='group_members_group_id_fkey'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], name='group_members_user_id_fkey'
        ),
    )
