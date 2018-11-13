"""Fix column settings

Revision ID: b553db89a76e
Revises: ccfad4d5e383
Create Date: 2018-11-13 22:34:43.992341

"""

# revision identifiers, used by Alembic.
revision = 'b553db89a76e'
down_revision = 'ccfad4d5e383'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('project', 'profile_id', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('project', 'inherit_sections', server_default=None)
    op.alter_column('ticket_type', 'name', existing_type=sa.String(80), type_=sa.String(250))
    op.alter_column('event', 'name', existing_type=sa.String(80), type_=sa.String(250))


def downgrade():
    op.alter_column('event', 'name', existing_type=sa.String(250), type_=sa.String(80))
    op.alter_column('ticket_type', 'name', existing_type=sa.String(250), type_=sa.String(80))
    op.alter_column('project', 'inherit_sections', server_default=True)
    op.alter_column('project', 'profile_id', existing_type=sa.INTEGER(), nullable=True)
