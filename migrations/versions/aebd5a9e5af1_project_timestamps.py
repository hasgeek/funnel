"""Project timestamps.

Revision ID: aebd5a9e5af1
Revises: d0097ec29880
Create Date: 2021-04-27 00:52:53.622787

"""

import progressbar.widgets
import sqlalchemy as sa
from alembic import op
from progressbar import ProgressBar
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = 'aebd5a9e5af1'
down_revision = 'd0097ec29880'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


project = table(
    'project',
    column('id', sa.Integer()),
    column('start_at', sa.TIMESTAMP(timezone=True)),
    column('end_at', sa.TIMESTAMP(timezone=True)),
)

session = table(
    'session',
    column('id', sa.Integer()),
    column('start_at', sa.Integer()),
    column('end_at', sa.Integer()),
    column('project_id', sa.Integer()),
)


def get_progressbar(label: str, maxval: int | None) -> ProgressBar:
    return ProgressBar(
        maxval=maxval,
        widgets=[
            label,
            ': ',
            progressbar.widgets.Percentage(),
            ' ',
            progressbar.widgets.Bar(),
            ' ',
            progressbar.widgets.ETA(),
            ' ',
        ],
    )


def upgrade() -> None:
    op.add_column(
        'project',
        sa.Column('first_published_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        'project', sa.Column('published_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        'project', sa.Column('start_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        'project', sa.Column('end_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.create_index(
        op.f('ix_project_published_at'), 'project', ['published_at'], unique=False
    )
    op.create_index(op.f('ix_project_start_at'), 'project', ['start_at'], unique=False)
    op.create_index(op.f('ix_project_end_at'), 'project', ['end_at'], unique=False)

    # Index existing timestamp and state columns
    op.create_index(
        op.f('ix_project_cfp_end_at'), 'project', ['cfp_end_at'], unique=False
    )
    op.create_index(
        op.f('ix_project_cfp_start_at'), 'project', ['cfp_start_at'], unique=False
    )
    op.create_index(op.f('ix_project_state'), 'project', ['state'], unique=False)
    op.create_index(
        op.f('ix_project_cfp_state'), 'project', ['cfp_state'], unique=False
    )
    op.create_index(
        op.f('ix_project_schedule_state'), 'project', ['schedule_state'], unique=False
    )

    # Update project start_at/end_at timestamps where sessions exist
    conn = op.get_bind()
    count = conn.scalar(sa.select(sa.func.count(sa.text('*'))).select_from(project))
    progress = get_progressbar("Projects", count)
    progress.start()
    project_ids = conn.execute(sa.select(project.c.id))
    for counter, row in enumerate(project_ids):
        start_at = conn.scalar(
            sa.select(sa.func.min(session.c.start_at))
            .where(session.c.start_at.is_not(None))
            .where(session.c.project_id == row.id)
        )
        if start_at is not None:
            end_at = conn.scalar(
                sa.select(sa.func.max(session.c.end_at))
                .where(session.c.end_at.is_not(None))
                .where(session.c.project_id == row.id)
            )
            conn.execute(
                project.update()
                .where(project.c.id == row.id)
                .values(start_at=start_at, end_at=end_at)
            )
        progress.update(counter)
    progress.finish()


def downgrade() -> None:
    op.drop_index(op.f('ix_project_schedule_state'), table_name='project')
    op.drop_index(op.f('ix_project_cfp_state'), table_name='project')
    op.drop_index(op.f('ix_project_state'), table_name='project')
    op.drop_index(op.f('ix_project_cfp_end_at'), table_name='project')
    op.drop_index(op.f('ix_project_cfp_start_at'), table_name='project')
    op.drop_index(op.f('ix_project_end_at'), table_name='project')
    op.drop_index(op.f('ix_project_start_at'), table_name='project')
    op.drop_index(op.f('ix_project_published_at'), table_name='project')
    op.drop_column('project', 'end_at')
    op.drop_column('project', 'start_at')
    op.drop_column('project', 'published_at')
    op.drop_column('project', 'first_published_at')
