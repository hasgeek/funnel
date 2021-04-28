"""Remove schedule state.

Revision ID: 08cef852ca39
Revises: 4aea03545045
Create Date: 2021-04-27 06:02:19.879566

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '08cef852ca39'
down_revision = '4aea03545045'
branch_labels = None
depends_on = None


SCHEDULE_STATE_PUBLISHED = 1


def upgrade():
    op.drop_index('ix_project_schedule_state', table_name='project')
    op.drop_column('project', 'schedule_state')


def downgrade():
    op.add_column(
        'project',
        sa.Column(
            'schedule_state',
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
            server_default=sa.text(str(SCHEDULE_STATE_PUBLISHED)),
        ),
    )
    op.alter_column('project', 'schedule_state', server_default=None)
    op.create_index(
        'ix_project_schedule_state', 'project', ['schedule_state'], unique=False
    )
