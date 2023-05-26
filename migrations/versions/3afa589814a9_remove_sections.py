"""Remove sections.

Revision ID: 3afa589814a9
Revises: 1b8fc63c0fb0
Create Date: 2019-06-06 15:06:04.690314

"""

# revision identifiers, used by Alembic.
revision = '3afa589814a9'
down_revision = '1b8fc63c0fb0'

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


def upgrade() -> None:
    op.drop_constraint('proposal_section_id_fkey', 'proposal', type_='foreignkey')
    op.drop_column('proposal', 'section_id')
    op.drop_table('section')
    op.drop_column('project', 'inherit_sections')


def downgrade() -> None:
    op.add_column(
        'project',
        sa.Column(
            'inherit_sections',
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )
    op.alter_column('project', 'inherit_sections', server_default=None)
    op.create_table(
        'section',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
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
        sa.Column('project_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('public', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('voteset_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('commentset_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=250), autoincrement=False, nullable=False),
        sa.Column('title', sa.VARCHAR(length=250), autoincrement=False, nullable=False),
        sa.CheckConstraint("(name)::text <> ''::text", name='section_name_check'),
        sa.ForeignKeyConstraint(
            ['commentset_id'], ['commentset.id'], name='section_commentset_id_fkey'
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'], name='section_project_id_fkey'
        ),
        sa.ForeignKeyConstraint(
            ['voteset_id'], ['voteset.id'], name='section_voteset_id_fkey'
        ),
        sa.PrimaryKeyConstraint('id', name='section_pkey'),
        sa.UniqueConstraint('project_id', 'name', name='section_project_id_name_key'),
    )
    op.add_column(
        'proposal',
        sa.Column('section_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'proposal_section_id_fkey', 'proposal', 'section', ['section_id'], ['id']
    )
