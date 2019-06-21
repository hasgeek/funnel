"""removed date, date_upto from project

Revision ID: c11dc931b903
Revises: 1829e53eba75
Create Date: 2019-06-08 10:58:13.772112

"""

# revision identifiers, used by Alembic.
revision = 'c11dc931b903'
down_revision = '1829e53eba75'

from alembic import op
import sqlalchemy as sa  # NOQA
from sqlalchemy.sql import table, column


project = table('project',
    column('id', sa.Integer()),
    column('date', sa.Date()),
    column('date_upto', sa.Date()),
    )


session = table('session',
    column('id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('start', sa.TIMESTAMP(timezone=True)),
    column('end', sa.TIMESTAMP(timezone=True))
    )


def upgrade():
    op.drop_column('project', 'date')
    op.drop_column('project', 'date_upto')


def downgrade():
    conn = op.get_bind()

    op.add_column('project', sa.Column('date', sa.Date(), nullable=True))
    op.add_column('project', sa.Column('date_upto', sa.Date(), nullable=True))

    projects = conn.execute(sa.select([project.c.id]))
    for project_id in projects:
        first_session = conn.execute(sa.select([session.c.start]).where(session.c.project_id == project_id[0]).where(session.c.start.isnot(None)).order_by(session.c.start.asc())).fetchone()
        if first_session is not None:
            conn.execute(sa.update(project).where(project.c.id == project_id[0]).values(date=first_session[0].date()))
        last_session = conn.execute(sa.select([session.c.end]).where(session.c.project_id == project_id[0]).where(session.c.end.isnot(None)).order_by(session.c.end.desc())).fetchone()
        if last_session is not None:
            conn.execute(sa.update(project).where(project.c.id == project_id[0]).values(date_upto=last_session[0].date()))
