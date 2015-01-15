"""Proposal fields are now optional

Revision ID: a2115fab4c4
Revises: 39af75387b10
Create Date: 2015-01-16 01:34:45.460775

"""

# revision identifiers, used by Alembic.
revision = 'a2115fab4c4'
down_revision = '39af75387b10'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('proposal', 'description_html',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('proposal', 'description_text',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('proposal', 'links',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('proposal', 'objective_html',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('proposal', 'objective_text',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('proposal', 'preview_video',
               existing_type=sa.VARCHAR(length=250),
               nullable=True)
    op.alter_column('proposal', 'requirements_html',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('proposal', 'requirements_text',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('proposal', 'session_type',
               existing_type=sa.VARCHAR(length=40),
               nullable=True)
    op.alter_column('proposal', 'slides',
               existing_type=sa.VARCHAR(length=250),
               nullable=True)
    op.alter_column('proposal', 'technical_level',
               existing_type=sa.VARCHAR(length=40),
               nullable=True)


def downgrade():
    op.alter_column('proposal', 'technical_level',
               existing_type=sa.VARCHAR(length=40),
               nullable=False)
    op.alter_column('proposal', 'slides',
               existing_type=sa.VARCHAR(length=250),
               nullable=False)
    op.alter_column('proposal', 'session_type',
               existing_type=sa.VARCHAR(length=40),
               nullable=False)
    op.alter_column('proposal', 'requirements_text',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('proposal', 'requirements_html',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('proposal', 'preview_video',
               existing_type=sa.VARCHAR(length=250),
               nullable=False)
    op.alter_column('proposal', 'objective_text',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('proposal', 'objective_html',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('proposal', 'links',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('proposal', 'description_text',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('proposal', 'description_html',
               existing_type=sa.TEXT(),
               nullable=False)
