"""Removed legacy_name from project.

Revision ID: 4b7fe9b25c6c
Revises: 252f9a705901
Create Date: 2019-05-30 12:33:00.598454

"""

# revision identifiers, used by Alembic.
revision = '4b7fe9b25c6c'
down_revision = '252f9a705901'

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

project = table(
    'project',
    column('profile_id', sa.Integer()),
    column('legacy_name', sa.Unicode(250)),
    column('name', sa.Unicode(250)),
)

profile = table('profile', column('id', sa.Integer()), column('name', sa.Unicode(250)))

legacy_data = [
    {'legacy_name': 'jsfoo2011', 'name': '2011', 'profile_name': 'jsfoo'},
    {'legacy_name': 'droidcon2012', 'name': '2012', 'profile_name': 'droidconin'},
    {
        'legacy_name': 'inboxalert',
        'name': '2013-tentative',
        'profile_name': 'inboxalert',
    },
    {
        'legacy_name': 'jsfoo-bangalore2012',
        'name': '2012-dummy',
        'profile_name': 'jsfoo',
    },
    {'legacy_name': 'inbox-alert-2014', 'name': '2014', 'profile_name': 'inboxalert'},
    {'legacy_name': 'metarefresh2013', 'name': '2013', 'profile_name': 'metarefresh'},
    {'legacy_name': 'jsfoo2013', 'name': '2013', 'profile_name': 'jsfoo'},
    {'legacy_name': 'fifthel2013', 'name': '2013', 'profile_name': 'fifthelephant'},
    {'legacy_name': '5el', 'name': '2012', 'profile_name': 'fifthelephant'},
    {'legacy_name': 'cartonama', 'name': '2012', 'profile_name': 'cartonama'},
    {'legacy_name': 'jsfoo-pune', 'name': '2012-pune', 'profile_name': 'jsfoo'},
    {'legacy_name': 'metarefresh', 'name': '2012', 'profile_name': 'metarefresh'},
    {'legacy_name': 'jsfoo', 'name': '2012', 'profile_name': 'jsfoo'},
    {'legacy_name': 'droidcon', 'name': '2011', 'profile_name': 'droidconin'},
    {'legacy_name': 'rootconf', 'name': '2012', 'profile_name': 'rootconf'},
    {
        'legacy_name': 'cartonama-workshop',
        'name': '2012-workshop',
        'profile_name': 'cartonama',
    },
    {'legacy_name': 'paystation', 'name': 'paystation', 'profile_name': 'miniconf'},
    {'legacy_name': 'jsfoo-chennai', 'name': '2012-chennai', 'profile_name': 'jsfoo'},
    {
        'legacy_name': 'css-workshop',
        'name': '2013-css-workshop',
        'profile_name': 'metarefresh',
    },
    {'legacy_name': 'phpcloud', 'name': '2011', 'profile_name': 'phpcloud'},
    {'legacy_name': 'fifthel2014', 'name': '2014', 'profile_name': 'fifthelephant'},
    {'legacy_name': 'droidcon2014', 'name': '2014', 'profile_name': 'droidconin'},
    {'legacy_name': 'jsfoo2014', 'name': '2014', 'profile_name': 'jsfoo'},
    {'legacy_name': 'metarefresh2015', 'name': '2015', 'profile_name': 'metarefresh'},
    {'legacy_name': 'rootconf2014', 'name': '2014', 'profile_name': 'rootconf'},
    {'legacy_name': 'metarefresh2014', 'name': '2014', 'profile_name': 'metarefresh'},
    {
        'legacy_name': 'angularjs-miniconf-2014',
        'name': '2014-angularjs',
        'profile_name': 'miniconf',
    },
    {'legacy_name': 'droidcon2013', 'name': '2013', 'profile_name': 'droidconin'},
    {
        'legacy_name': 'redis-miniconf-2014',
        'name': '2014-redis',
        'profile_name': 'miniconf',
    },
    {
        'legacy_name': 'rootconf-miniconf-2014',
        'name': '2014-rootconf',
        'profile_name': 'miniconf',
    },
]


def upgrade() -> None:
    op.drop_column('project', 'legacy_name')


def downgrade() -> None:
    conn = op.get_bind()

    op.add_column(
        'project', sa.Column('legacy_name', sa.Unicode(length=250), nullable=True)
    )
    op.create_unique_constraint('project_legacy_name_key', 'project', ['legacy_name'])

    for data in legacy_data:
        profile_id = conn.execute(
            sa.select(profile.c.id)
            .where(profile.c.name == data['profile_name'])
            .limit(1)
        ).fetchone()
        if profile_id:
            conn.execute(
                sa.update(project)
                .where(project.c.name == data['name'])
                .where(project.c.profile_id == profile_id[0])
                .values({'legacy_name': data['legacy_name']})
            )
