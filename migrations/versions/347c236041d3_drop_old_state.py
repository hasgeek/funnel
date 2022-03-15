"""Drop old state from project model.

Revision ID: 347c236041d3
Revises: 4b80fb451c8e
Create Date: 2019-03-06 16:34:55.226219

"""

revision = '347c236041d3'
down_revision = '4b80fb451c8e'

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa


class OLD_STATE:
    DRAFT = 0
    SUBMISSIONS = 1
    VOTING = 2
    JURY = 3
    FEEDBACK = 4
    CLOSED = 5
    WITHDRAWN = 6


class PROJECT_STATE:
    DRAFT = 0
    PUBLISHED = 1
    WITHDRAWN = 2
    DELETED = 3


class CFP_STATE:
    NONE = 0
    PUBLIC = 1
    CLOSED = 2


project = table(
    'project',
    column('created_at', sa.DateTime()),
    column('state', sa.Integer()),
    column('old_state', sa.Integer()),
    column('cfp_state', sa.Integer()),
    column('cfp_start_at', sa.DateTime()),
    column('schedule_state', sa.Integer()),
)


downgrade_states = {
    OLD_STATE.DRAFT: (PROJECT_STATE.DRAFT, CFP_STATE.NONE, None),
    OLD_STATE.SUBMISSIONS: (
        PROJECT_STATE.PUBLISHED,
        CFP_STATE.PUBLIC,
        project.c.created_at,
    ),
    OLD_STATE.VOTING: (PROJECT_STATE.PUBLISHED, CFP_STATE.CLOSED, None),
    OLD_STATE.JURY: (PROJECT_STATE.PUBLISHED, CFP_STATE.CLOSED, None),
    OLD_STATE.FEEDBACK: (PROJECT_STATE.PUBLISHED, CFP_STATE.CLOSED, None),
    OLD_STATE.CLOSED: (PROJECT_STATE.PUBLISHED, CFP_STATE.CLOSED, None),
    OLD_STATE.WITHDRAWN: (PROJECT_STATE.WITHDRAWN, CFP_STATE.CLOSED, None),
}


def upgrade():
    op.drop_constraint('project_old_state_check', 'project', type_='check')
    op.drop_column('project', 'old_state')


def downgrade():
    op.add_column(
        'project',
        sa.Column(
            'old_state',
            sa.Integer(),
            nullable=False,
            server_default=str(OLD_STATE.DRAFT),
        ),
    )
    op.alter_column('project', 'old_state', server_default=None)
    op.create_check_constraint(
        'project_old_state_check', 'project', 'old_state IN (0, 1, 2, 3, 4, 5, 6)'
    )

    for old_state, new_state in downgrade_states.items():
        op.execute(
            project.update()
            .where(project.c.state == new_state[0])
            .where(project.c.cfp_state == new_state[1])
            .values({'old_state': old_state})
        )
