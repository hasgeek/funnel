"""Migrations for using MarkdownComposite 

Revision ID: 9d513be1a96
Revises: 5290f9238875
Create Date: 2013-09-05 16:01:17.681404

"""

# revision identifiers, used by Alembic.
revision = '9d513be1a96'
down_revision = '5290f9238875'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('comment', 'message', new_column_name='message_text')
    op.alter_column('proposal', 'objective', new_column_name='objective_text')
    op.alter_column('proposal', 'bio', new_column_name='bio_text')
    op.alter_column('proposal', 'requirements', new_column_name='requirements_text')
    op.alter_column('proposal', 'description', new_column_name='description_text')
    op.alter_column('proposal_space', 'description', new_column_name='description_text')


def downgrade():
    op.alter_column('comment', 'message_text', new_column_name='message')
    op.alter_column('proposal', 'objective_text', new_column_name='objective')
    op.alter_column('proposal', 'bio_text', new_column_name='bio')
    op.alter_column('proposal', 'requirements_text', new_column_name='requirements')
    op.alter_column('proposal', 'description_text', new_column_name='description')
    op.alter_column('proposal_space', 'description_text', new_column_name='description')
