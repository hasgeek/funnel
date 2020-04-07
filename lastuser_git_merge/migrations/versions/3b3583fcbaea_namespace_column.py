# -*- coding: utf-8 -*-
"""namespace column

Revision ID: 3b3583fcbaea
Revises: 7b0ba76b89e
Create Date: 2013-11-10 00:21:06.881127

"""

# revision identifiers, used by Alembic.
revision = '3b3583fcbaea'
down_revision = '7b0ba76b89e'

from alembic import op
from sqlalchemy.sql import bindparam, column, select, table
import sqlalchemy as sa

from coaster.utils import namespace_from_url


def upgrade():
    op.add_column(
        'client', sa.Column('namespace', sa.Unicode(length=250), nullable=True)
    )
    op.create_unique_constraint('client_namespace_key', 'client', ['namespace'])

    connection = op.get_bind()
    client = table(
        'client',
        column('id', sa.Integer),
        column('website', sa.Unicode(250)),
        column('namespace', sa.Unicode(250)),
    )
    results = connection.execute(select([client.c.id, client.c.website]))
    namespaces = []
    namespace_list = []
    for r in results:
        new_namespace = namespace = namespace_from_url(r[1])
        append_count = 0
        while new_namespace in namespace_list:
            append_count = append_count + 1
            new_namespace = "%s%s" % (namespace, append_count)
        namespaces.append({'clientid': r[0], 'namespace': new_namespace})
        namespace_list.append(new_namespace)

    if len(namespaces) > 0:
        updt_stmt = (
            client.update()
            .where(client.c.id == bindparam('clientid'))
            .values(namespace=bindparam('namespace'))
        )
        connection.execute(updt_stmt, namespaces)


def downgrade():
    op.drop_column('client', 'namespace')
