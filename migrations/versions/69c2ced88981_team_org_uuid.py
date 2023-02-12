"""Team org UUID.

Revision ID: 69c2ced88981
Revises: b34aa62af7fc
Create Date: 2018-12-07 20:21:02.169857

"""

# revision identifiers, used by Alembic.
revision = '69c2ced88981'
down_revision = 'b34aa62af7fc'

from alembic import op
from sqlalchemy.sql import column, table
from sqlalchemy_utils import UUIDType
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

from coaster.utils import buid2uuid, uuid2buid

team = table(
    'team',
    column('id', sa.Integer()),
    column('orgid', sa.String(22)),
    column('org_uuid', UUIDType(binary=False)),
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

    op.add_column('team', sa.Column('org_uuid', UUIDType(binary=False), nullable=True))
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(team))
    progress = get_progressbar("Teams", count)
    progress.start()
    items = conn.execute(sa.select(team.c.id, team.c.orgid))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(team)
            .where(team.c.id == item.id)
            .values(org_uuid=buid2uuid(item.orgid))
        )
        progress.update(counter)
    progress.finish()
    op.alter_column('team', 'org_uuid', nullable=False)
    op.create_index('ix_team_org_uuid', 'team', ['org_uuid'], unique=False)
    op.drop_index('ix_team_orgid', table_name='team')
    op.drop_column('team', 'orgid')


def downgrade():
    conn = op.get_bind()

    op.add_column(
        'team', sa.Column('orgid', sa.String(22), autoincrement=False, nullable=True)
    )
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(team))
    progress = get_progressbar("Teams", count)
    progress.start()
    items = conn.execute(sa.select(team.c.id, team.c.org_uuid))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(team)
            .where(team.c.id == item.id)
            .values(orgid=uuid2buid(item.org_uuid))
        )
        progress.update(counter)
    progress.finish()
    op.alter_column('team', 'orgid', nullable=False)
    op.create_index('ix_team_orgid', 'team', ['orgid'], unique=False)
    op.drop_index('ix_team_org_uuid', table_name='team')
    op.drop_column('team', 'org_uuid')
