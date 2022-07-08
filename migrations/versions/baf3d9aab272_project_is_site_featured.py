"""Project is site_featured.

Revision ID: baf3d9aab272
Revises: a5dbb3f843e4
Create Date: 2021-04-27 20:53:03.375954

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'baf3d9aab272'
down_revision = 'a5dbb3f843e4'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('project', 'featured', new_column_name='site_featured')


def downgrade():
    op.alter_column('project', 'site_featured', new_column_name='featured')
