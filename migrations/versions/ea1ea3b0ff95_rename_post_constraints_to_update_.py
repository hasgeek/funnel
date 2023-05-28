"""Rename Post constraints to Update constraints.

Revision ID: ea1ea3b0ff95
Revises: 851473d61beb
Create Date: 2020-08-08 08:40:19.751509

"""

from textwrap import dedent
from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ea1ea3b0ff95'
down_revision = '851473d61beb'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

# (old, new)
renamed_constraints = [
    ("post_commentset_id_fkey", "update_commentset_id_fkey"),
    ("post_deleted_by_id_fkey", "update_deleted_by_id_fkey"),
    ("post_project_id_fkey", "update_project_id_fkey"),
    ("post_published_by_id_fkey", "update_published_by_id_fkey"),
    ("post_user_id_fkey", "update_user_id_fkey"),
    ("post_voteset_id_fkey", "update_voteset_id_fkey"),
]


def upgrade() -> None:
    op.alter_column('update', 'project_id', existing_type=sa.INTEGER(), nullable=False)
    for old, new in renamed_constraints:
        op.execute(sa.DDL(f'ALTER TABLE update RENAME CONSTRAINT "{old}" TO "{new}"'))

    op.execute(
        sa.DDL(
            dedent(
                '''
        DROP TRIGGER post_search_vector_trigger ON update;
        DROP FUNCTION post_search_vector_update();
        '''
            )
        )
    )

    op.execute(
        sa.DDL(
            dedent(
                '''
        CREATE FUNCTION update_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.body_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER update_search_vector_trigger BEFORE INSERT OR UPDATE ON update
        FOR EACH ROW EXECUTE PROCEDURE update_search_vector_update();
                '''
            )
        )
    )


def downgrade() -> None:
    op.execute(
        sa.DDL(
            dedent(
                '''
        DROP TRIGGER update_search_vector_trigger ON update;
        DROP FUNCTION update_search_vector_update();
        '''
            )
        )
    )

    op.execute(
        sa.DDL(
            dedent(
                '''
        CREATE FUNCTION post_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.body_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER post_search_vector_trigger BEFORE INSERT OR UPDATE ON update
        FOR EACH ROW EXECUTE PROCEDURE post_search_vector_update();
                '''
            )
        )
    )

    for old, new in renamed_constraints:
        op.execute(sa.DDL(f'ALTER TABLE update RENAME CONSTRAINT "{new}" TO "{old}"'))
    op.alter_column('update', 'project_id', existing_type=sa.INTEGER(), nullable=True)
