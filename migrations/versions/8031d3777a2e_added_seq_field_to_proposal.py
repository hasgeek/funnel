"""Added seq field to Proposal.

Revision ID: 8031d3777a2e
Revises: 284c10efdbce
Create Date: 2021-02-19 09:22:18.046986

"""

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

# revision identifiers, used by Alembic.
revision = '8031d3777a2e'
down_revision = '284c10efdbce'
branch_labels = None
depends_on = None


project = table(
    'project',
    column('id', sa.Integer()),
)


proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('url_id', sa.Integer()),
    column('seq', sa.Integer()),
)


def get_progressbar(label, maxval):
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


def upgrade():
    conn = op.get_bind()

    op.add_column('proposal', sa.Column('seq', sa.Integer(), nullable=True))
    op.create_unique_constraint(
        'proposal_project_id_seq_key', 'proposal', ['project_id', 'seq']
    )

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(project))
    progress = get_progressbar("Projects", count)
    progress.start()

    projects = conn.execute(sa.select([project.c.id]))
    for counter, project_item in enumerate(projects):
        proposals = conn.execute(
            sa.select([proposal.c.id, proposal.c.url_id, proposal.c.seq])
            .where(proposal.c.project_id == project_item.id)
            .select_from(proposal)
            .order_by(proposal.c.url_id.asc())
        )

        for proposal_counter, proposal_item in enumerate(proposals):
            conn.execute(
                sa.update(proposal)
                .where(sa.and_(proposal.c.id == proposal_item.id))
                .values(seq=(proposal_counter + 1) * 1000)
            )
        progress.update(counter)
    progress.finish()

    op.alter_column('proposal', 'seq', nullable=False)


def downgrade():
    op.drop_constraint('proposal_project_id_seq_key', 'proposal', type_='unique')
    op.drop_column('proposal', 'seq')
