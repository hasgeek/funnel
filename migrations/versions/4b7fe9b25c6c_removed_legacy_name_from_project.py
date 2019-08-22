# -*- coding: utf-8 -*-

"""removed legacy_name from project

Revision ID: 4b7fe9b25c6c
Revises: 252f9a705901
Create Date: 2019-05-30 12:33:00.598454

"""

# revision identifiers, used by Alembic.
revision = '4b7fe9b25c6c'
down_revision = '252f9a705901'

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa  # NOQA

project = table(
    'project',
    column('profile_id', sa.Integer()),
    column('legacy_name', sa.Unicode(250)),
    column('name', sa.Unicode(250)),
)

profile = table('profile', column('id', sa.Integer()), column('name', sa.Unicode(250)))

legacy_data = [
    {'legacy_name': u'jsfoo2011', 'name': u'2011', 'profile_name': u'jsfoo'},
    {'legacy_name': u'droidcon2012', 'name': u'2012', 'profile_name': u'droidconin'},
    {
        'legacy_name': u'inboxalert',
        'name': u'2013-tentative',
        'profile_name': u'inboxalert',
    },
    {
        'legacy_name': u'jsfoo-bangalore2012',
        'name': u'2012-dummy',
        'profile_name': u'jsfoo',
    },
    {
        'legacy_name': u'inbox-alert-2014',
        'name': u'2014',
        'profile_name': u'inboxalert',
    },
    {
        'legacy_name': u'metarefresh2013',
        'name': u'2013',
        'profile_name': u'metarefresh',
    },
    {'legacy_name': u'jsfoo2013', 'name': u'2013', 'profile_name': u'jsfoo'},
    {'legacy_name': u'fifthel2013', 'name': u'2013', 'profile_name': u'fifthelephant'},
    {'legacy_name': u'5el', 'name': u'2012', 'profile_name': u'fifthelephant'},
    {'legacy_name': u'cartonama', 'name': u'2012', 'profile_name': u'cartonama'},
    {'legacy_name': u'jsfoo-pune', 'name': u'2012-pune', 'profile_name': u'jsfoo'},
    {'legacy_name': u'metarefresh', 'name': u'2012', 'profile_name': u'metarefresh'},
    {'legacy_name': u'jsfoo', 'name': u'2012', 'profile_name': u'jsfoo'},
    {'legacy_name': u'droidcon', 'name': u'2011', 'profile_name': u'droidconin'},
    {'legacy_name': u'rootconf', 'name': u'2012', 'profile_name': u'rootconf'},
    {
        'legacy_name': u'cartonama-workshop',
        'name': u'2012-workshop',
        'profile_name': u'cartonama',
    },
    {'legacy_name': u'paystation', 'name': u'paystation', 'profile_name': u'miniconf'},
    {
        'legacy_name': u'jsfoo-chennai',
        'name': u'2012-chennai',
        'profile_name': u'jsfoo',
    },
    {
        'legacy_name': u'css-workshop',
        'name': u'2013-css-workshop',
        'profile_name': u'metarefresh',
    },
    {'legacy_name': u'phpcloud', 'name': u'2011', 'profile_name': u'phpcloud'},
    {'legacy_name': u'fifthel2014', 'name': u'2014', 'profile_name': u'fifthelephant'},
    {'legacy_name': u'droidcon2014', 'name': u'2014', 'profile_name': u'droidconin'},
    {'legacy_name': u'jsfoo2014', 'name': u'2014', 'profile_name': u'jsfoo'},
    {
        'legacy_name': u'metarefresh2015',
        'name': u'2015',
        'profile_name': u'metarefresh',
    },
    {'legacy_name': u'rootconf2014', 'name': u'2014', 'profile_name': u'rootconf'},
    {
        'legacy_name': u'metarefresh2014',
        'name': u'2014',
        'profile_name': u'metarefresh',
    },
    {
        'legacy_name': u'angularjs-miniconf-2014',
        'name': u'2014-angularjs',
        'profile_name': u'miniconf',
    },
    {'legacy_name': u'droidcon2013', 'name': u'2013', 'profile_name': u'droidconin'},
    {
        'legacy_name': u'redis-miniconf-2014',
        'name': u'2014-redis',
        'profile_name': u'miniconf',
    },
    {
        'legacy_name': u'rootconf-miniconf-2014',
        'name': u'2014-rootconf',
        'profile_name': u'miniconf',
    },
]


def upgrade():
    op.drop_column('project', 'legacy_name')


def downgrade():
    conn = op.get_bind()

    op.add_column(
        'project', sa.Column('legacy_name', sa.Unicode(length=250), nullable=True)
    )
    op.create_unique_constraint('project_legacy_name_key', 'project', ['legacy_name'])

    for data in legacy_data:
        profile_id = conn.execute(
            sa.select([profile.c.id])
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
