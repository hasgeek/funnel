"""Primary venue

Revision ID: ae68621248af
Revises: 2441cb4f44d4
Create Date: 2018-11-23 01:52:58.790889

"""

# revision identifiers, used by Alembic.
revision = 'ae68621248af'
down_revision = '2441cb4f44d4'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.create_table('project_venue_primary',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('venue_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['venue_id'], ['venue.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('project_id')
        )
    # This SQL function prevents project.primary_venue from pointing to a venue
    # in another project. It does not prevent a venue from being moved to a
    # different project, thereby leaving the primary_venue record invalid.
    op.execute(sa.DDL('''
        CREATE FUNCTION project_venue_primary_validate() RETURNS TRIGGER AS $$
        DECLARE
            target RECORD;
        BEGIN
            IF (NEW.venue_id IS NOT NULL) THEN
                SELECT project_id INTO target FROM venue WHERE id = NEW.venue_id;
                IF (target.project_id != NEW.project_id) THEN
                    RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER project_venue_primary_trigger BEFORE INSERT OR UPDATE
        ON project_venue_primary
        FOR EACH ROW EXECUTE PROCEDURE project_venue_primary_validate();
    '''))
    op.execute(sa.DDL('''
        INSERT INTO project_venue_primary (project_id, venue_id, created_at, updated_at)
        SELECT DISTINCT ON (project_id) project_id, id, created_at, updated_at
        FROM venue
        ORDER BY project_id, created_at;
    '''))


def downgrade():
    op.execute(sa.DDL('''
        DROP TRIGGER project_venue_primary_trigger ON project_venue_primary;
        DROP FUNCTION project_venue_primary_validate();
    '''))
    op.drop_table('project_venue_primary')
