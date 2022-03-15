"""Project tri-state columns.

Revision ID: 4b80fb451c8e
Revises: e3bf172763bc
Create Date: 2019-02-07 01:55:47.123273

"""

# revision identifiers, used by Alembic.
revision = '4b80fb451c8e'
down_revision = '9aa60ff2a0ea'

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


class SCHEDULE_STATE:
    DRAFT = 0
    PUBLISHED = 1


project = table(
    'project',
    column('created_at', sa.DateTime()),
    column('old_state', sa.Integer()),
    column('state', sa.Integer()),
    column('cfp_state', sa.Integer()),
    column('cfp_start_at', sa.DateTime()),
    column('schedule_state', sa.Integer()),
)


upgrade_states = {
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
    # Move `state` out of the way into `old_state`
    op.alter_column('project', 'state', new_column_name='old_state')
    op.execute(
        sa.DDL(
            'ALTER TABLE project RENAME CONSTRAINT project_state_check TO project_old_state_check'
        )
    )

    # Create three new columns: `state`, `cfp_state` and `schedule_state`, with matching
    # CHECK constraints
    op.add_column(
        'project',
        sa.Column(
            'state',
            sa.Integer(),
            nullable=False,
            server_default=str(PROJECT_STATE.DRAFT),
        ),
    )
    op.alter_column('project', 'state', server_default=None)
    op.create_check_constraint(
        'project_state_check', 'project', 'state IN (0, 1, 2, 3)'
    )

    op.add_column(
        'project',
        sa.Column(
            'cfp_state',
            sa.Integer(),
            nullable=False,
            server_default=str(CFP_STATE.NONE),
        ),
    )
    op.alter_column('project', 'cfp_state', server_default=None)
    op.create_check_constraint(
        'project_cfp_state_check', 'project', 'cfp_state IN (0, 1, 2)'
    )

    op.add_column(
        'project',
        sa.Column(
            'schedule_state',
            sa.Integer(),
            nullable=False,
            server_default=str(SCHEDULE_STATE.DRAFT),
        ),
    )
    op.alter_column('project', 'schedule_state', server_default=None)
    op.create_check_constraint(
        'project_schedule_state_check', 'project', 'schedule_state IN (0, 1)'
    )

    op.add_column('project', sa.Column('cfp_start_at', sa.DateTime(), nullable=True))
    op.add_column('project', sa.Column('cfp_end_at', sa.DateTime(), nullable=True))

    for old_state, new_state in upgrade_states.items():
        op.execute(
            project.update()
            .where(project.c.old_state == old_state)
            .values(
                {
                    'state': new_state[0],
                    'cfp_state': new_state[1],
                    'cfp_start_at': new_state[2],
                }
            )
        )

    # For existing projects, assume the presence of a session to indicate a published schedule.
    # New projects will require explicit publication.
    op.execute(
        sa.DDL(
            'UPDATE project SET schedule_state=1 WHERE id IN (SELECT DISTINCT(project_id) FROM session)'
        )
    )


def downgrade():
    op.drop_column('project', 'cfp_end_at')
    op.drop_column('project', 'cfp_start_at')
    op.drop_constraint('project_state_check', 'project', type_='check')
    op.drop_column('project', 'state')
    op.drop_constraint('project_schedule_state_check', 'project', type_='check')
    op.drop_column('project', 'schedule_state')
    op.drop_constraint('project_cfp_state_check', 'project', type_='check')
    op.drop_column('project', 'cfp_state')

    op.alter_column('project', 'old_state', new_column_name='state')
    op.execute(
        sa.DDL(
            'ALTER TABLE project RENAME CONSTRAINT project_old_state_check TO project_state_check'
        )
    )
