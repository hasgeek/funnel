# -*- coding: utf-8 -*-

"""Add search vectors

Revision ID: 1829e53eba75
Revises: 752dee4ae101
Create Date: 2019-06-09 23:41:24.007858

"""

# revision identifiers, used by Alembic.
revision = '1829e53eba75'
down_revision = '752dee4ae101'

from textwrap import dedent

from alembic import op
from sqlalchemy_utils import TSVectorType
import sqlalchemy as sa  # NOQA


def upgrade():
    op.add_column('comment', sa.Column('search_vector', TSVectorType(), nullable=True))
    op.create_index(
        'ix_comment_search_vector',
        'comment',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    op.add_column('label', sa.Column('search_vector', TSVectorType(), nullable=True))
    op.create_index(
        'ix_label_search_vector',
        'label',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    op.add_column('profile', sa.Column('search_vector', TSVectorType(), nullable=True))
    op.create_index(
        'ix_profile_search_vector',
        'profile',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    op.add_column('project', sa.Column('search_vector', TSVectorType(), nullable=True))
    op.create_index(
        'ix_project_search_vector',
        'project',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    op.add_column('proposal', sa.Column('search_vector', TSVectorType(), nullable=True))
    op.create_index(
        'ix_proposal_search_vector',
        'proposal',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    op.add_column('session', sa.Column('search_vector', TSVectorType(), nullable=True))
    op.create_index(
        'ix_session_search_vector',
        'session',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    # Update search vectors for existing data
    op.execute(
        sa.DDL(
            dedent(
                '''
        UPDATE comment SET search_vector = setweight(to_tsvector('english', COALESCE(message_text, '')), 'A');

        UPDATE label SET search_vector = setweight(to_tsvector('english', COALESCE(name, '')), 'A') || setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(description, '')), 'B');

        UPDATE profile SET search_vector = setweight(to_tsvector('english', COALESCE(name, '')), 'A') || setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B');

        UPDATE project SET search_vector = setweight(to_tsvector('english', COALESCE(name, '')), 'A') || setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(instructions_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(location, '')), 'C');

        UPDATE proposal SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(abstract_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(outline_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(requirements_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(slides, '')), 'B') || setweight(to_tsvector('english', COALESCE(preview_video, '')), 'C') || setweight(to_tsvector('english', COALESCE(links, '')), 'B') || setweight(to_tsvector('english', COALESCE(bio_text, '')), 'B');

        UPDATE session SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(speaker_bio_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(speaker, '')), 'A');
        '''
            )
        )
    )

    # Create trigger functions and add triggers
    op.execute(
        sa.DDL(
            dedent(
                '''
        CREATE FUNCTION comment_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.message_text, '')), 'A');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER comment_search_vector_trigger BEFORE INSERT OR UPDATE ON comment
        FOR EACH ROW EXECUTE PROCEDURE comment_search_vector_update();

        CREATE FUNCTION label_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER label_search_vector_trigger BEFORE INSERT OR UPDATE ON label
        FOR EACH ROW EXECUTE PROCEDURE label_search_vector_update();

        CREATE FUNCTION profile_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER profile_search_vector_trigger BEFORE INSERT OR UPDATE ON profile
        FOR EACH ROW EXECUTE PROCEDURE profile_search_vector_update();

        CREATE FUNCTION project_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.instructions_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER project_search_vector_trigger BEFORE INSERT OR UPDATE ON project
        FOR EACH ROW EXECUTE PROCEDURE project_search_vector_update();

        CREATE FUNCTION proposal_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.abstract_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.outline_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.requirements_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.slides, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.preview_video, '')), 'C') || setweight(to_tsvector('english', COALESCE(NEW.links, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.bio_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER proposal_search_vector_trigger BEFORE INSERT OR UPDATE ON proposal
        FOR EACH ROW EXECUTE PROCEDURE proposal_search_vector_update();

        CREATE FUNCTION session_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.speaker_bio_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.speaker, '')), 'A');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER session_search_vector_trigger BEFORE INSERT OR UPDATE ON session
        FOR EACH ROW EXECUTE PROCEDURE session_search_vector_update();
        '''
            )
        )
    )

    op.alter_column('comment', 'search_vector', nullable=False)
    op.alter_column('label', 'search_vector', nullable=False)
    op.alter_column('profile', 'search_vector', nullable=False)
    op.alter_column('project', 'search_vector', nullable=False)
    op.alter_column('proposal', 'search_vector', nullable=False)
    op.alter_column('session', 'search_vector', nullable=False)


def downgrade():
    # Drop triggers and functions
    op.execute(
        sa.DDL(
            dedent(
                '''
        DROP TRIGGER comment_search_vector_trigger ON comment;
        DROP FUNCTION comment_search_vector_update();

        DROP TRIGGER label_search_vector_trigger ON label;
        DROP FUNCTION label_search_vector_update();

        DROP TRIGGER profile_search_vector_trigger ON profile;
        DROP FUNCTION profile_search_vector_update();

        DROP TRIGGER project_search_vector_trigger ON project;
        DROP FUNCTION project_search_vector_update();

        DROP TRIGGER proposal_search_vector_trigger ON proposal;
        DROP FUNCTION proposal_search_vector_update();

        DROP TRIGGER session_search_vector_trigger ON session;
        DROP FUNCTION session_search_vector_update();
        '''
            )
        )
    )

    op.drop_index('ix_session_search_vector', table_name='session')
    op.drop_column('session', 'search_vector')
    op.drop_index('ix_proposal_search_vector', table_name='proposal')
    op.drop_column('proposal', 'search_vector')
    op.drop_index('ix_project_search_vector', table_name='project')
    op.drop_column('project', 'search_vector')
    op.drop_index('ix_profile_search_vector', table_name='profile')
    op.drop_column('profile', 'search_vector')
    op.drop_index('ix_label_search_vector', table_name='label')
    op.drop_column('label', 'search_vector')
    op.drop_index('ix_comment_search_vector', table_name='comment')
    op.drop_column('comment', 'search_vector')
