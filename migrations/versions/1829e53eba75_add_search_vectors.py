"""Add search vectors

Revision ID: 1829e53eba75
Revises: 752dee4ae101
Create Date: 2019-06-09 23:41:24.007858

"""

# revision identifiers, used by Alembic.
revision = '1829e53eba75'
down_revision = '752dee4ae101'

from alembic import op
import sqlalchemy as sa  # NOQA
from sqlalchemy_utils import TSVectorType
from sqlalchemy_searchable import sync_trigger


# Borrowed from
# https://github.com/kvesteri/sqlalchemy-searchable/blob/master/sqlalchemy_searchable/expressions.sql
expressions = '''
DROP TYPE IF EXISTS tsq_state CASCADE;

CREATE TYPE tsq_state AS (
    search_query text,
    parentheses_stack int,
    skip_for int,
    current_token text,
    current_index int,
    current_char text,
    previous_char text,
    tokens text[]
);

CREATE OR REPLACE FUNCTION tsq_append_current_token(state tsq_state)
RETURNS tsq_state AS $$
BEGIN
    IF state.current_token != '' THEN
        state.tokens := array_append(state.tokens, state.current_token);
        state.current_token := '';
    END IF;
    RETURN state;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION tsq_tokenize_character(state tsq_state)
RETURNS tsq_state AS $$
BEGIN
    IF state.current_char = '(' THEN
        state.tokens := array_append(state.tokens, '(');
        state.parentheses_stack := state.parentheses_stack + 1;
        state := tsq_append_current_token(state);
    ELSIF state.current_char = ')' THEN
        IF (state.parentheses_stack > 0 AND state.current_token != '') THEN
            state := tsq_append_current_token(state);
            state.tokens := array_append(state.tokens, ')');
            state.parentheses_stack := state.parentheses_stack - 1;
        END IF;
    ELSIF state.current_char = '"' THEN
        state.skip_for := position('"' IN substring(
            state.search_query FROM state.current_index + 1
        ));

        IF state.skip_for > 1 THEN
            state.tokens = array_append(
                state.tokens,
                substring(
                    state.search_query
                    FROM state.current_index FOR state.skip_for + 1
                )
            );
        ELSIF state.skip_for = 0 THEN
            state.current_token := state.current_token || state.current_char;
        END IF;
    ELSIF (
        state.current_char = '-' AND
        (state.current_index = 1 OR state.previous_char = ' ')
    ) THEN
        state.tokens := array_append(state.tokens, '-');
    ELSIF state.current_char = ' ' THEN
        state := tsq_append_current_token(state);
        IF substring(
            state.search_query FROM state.current_index FOR 4
        ) = ' or ' THEN
            state.skip_for := 2;

            -- remove duplicate OR tokens
            IF state.tokens[array_length(state.tokens, 1)] != ' | ' THEN
                state.tokens := array_append(state.tokens, ' | ');
            END IF;
        END IF;
    ELSE
        state.current_token = state.current_token || state.current_char;
    END IF;
    RETURN state;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION tsq_tokenize(search_query text) RETURNS text[] AS $$
DECLARE
    state tsq_state;
BEGIN
    SELECT
        search_query::text AS search_query,
        0::int AS parentheses_stack,
        0 AS skip_for,
        ''::text AS current_token,
        0 AS current_index,
        ''::text AS current_char,
        ''::text AS previous_char,
        '{}'::text[] AS tokens
    INTO state;

    state.search_query := lower(trim(
        regexp_replace(search_query, '""+', '""', 'g')
    ));

    FOR state.current_index IN (
        SELECT generate_series(1, length(state.search_query))
    ) LOOP
        state.current_char := substring(
            search_query FROM state.current_index FOR 1
        );

        IF state.skip_for > 0 THEN
            state.skip_for := state.skip_for - 1;
            CONTINUE;
        END IF;

        state := tsq_tokenize_character(state);
        state.previous_char := state.current_char;
    END LOOP;
    state := tsq_append_current_token(state);

    state.tokens := array_nremove(state.tokens, '(', -state.parentheses_stack);

    RETURN state.tokens;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Processes an array of text search tokens and returns a tsquery
CREATE OR REPLACE FUNCTION tsq_process_tokens(config regconfig, tokens text[])
RETURNS tsquery AS $$
DECLARE
    result_query text;
    previous_value text;
    value text;
BEGIN
    result_query := '';
    FOREACH value IN ARRAY tokens LOOP
        IF value = '"' THEN
            CONTINUE;
        END IF;

        IF left(value, 1) = '"' AND right(value, 1) = '"' THEN
            value := phraseto_tsquery(config, value);
        ELSIF value NOT IN ('(', ' | ', ')', '-') THEN
            value := quote_literal(value) || ':*';
        END IF;

        IF previous_value = '-' THEN
            IF value = '(' THEN
                value := '!' || value;
            ELSE
                value := '!(' || value || ')';
            END IF;
        END IF;

        SELECT
            CASE
                WHEN result_query = '' THEN value
                WHEN (
                    previous_value IN ('!(', '(', ' | ') OR
                    value IN (')', ' | ')
                ) THEN result_query || value
                ELSE result_query || ' & ' || value
            END
        INTO result_query;
        previous_value := value;
    END LOOP;

    RETURN to_tsquery(config, result_query);
END;
$$ LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION tsq_process_tokens(tokens text[])
RETURNS tsquery AS $$
    SELECT tsq_process_tokens(get_current_ts_config(), tokens);
$$ LANGUAGE SQL IMMUTABLE;


CREATE OR REPLACE FUNCTION tsq_parse(config regconfig, search_query text)
RETURNS tsquery AS $$
    SELECT tsq_process_tokens(config, tsq_tokenize(search_query));
$$ LANGUAGE SQL IMMUTABLE;


CREATE OR REPLACE FUNCTION tsq_parse(config text, search_query text)
RETURNS tsquery AS $$
    SELECT tsq_parse(config::regconfig, search_query);
$$ LANGUAGE SQL IMMUTABLE;


CREATE OR REPLACE FUNCTION tsq_parse(search_query text) RETURNS tsquery AS $$
    SELECT tsq_parse(get_current_ts_config(), search_query);
$$ LANGUAGE SQL IMMUTABLE;


-- remove first N elements equal to the given value from the array (array
-- must be one-dimensional)
--
-- If negative value is given as the third argument the removal of elements
-- starts from the last array element.
CREATE OR REPLACE FUNCTION array_nremove(anyarray, anyelement, int)
RETURNS ANYARRAY AS $$
    WITH replaced_positions AS (
        SELECT UNNEST(
            CASE
            WHEN $2 IS NULL THEN
                '{}'::int[]
            WHEN $3 > 0 THEN
                (array_positions($1, $2))[1:$3]
            WHEN $3 < 0 THEN
                (array_positions($1, $2))[
                    (cardinality(array_positions($1, $2)) + $3 + 1):
                ]
            ELSE
                '{}'::int[]
            END
        ) AS position
    )
    SELECT COALESCE((
        SELECT array_agg(value)
        FROM unnest($1) WITH ORDINALITY AS t(value, index)
        WHERE index NOT IN (SELECT position FROM replaced_positions)
    ), $1[1:0]);
$$ LANGUAGE SQL IMMUTABLE;
'''

drop_expressions = '''
DROP FUNCTION array_nremove(anyarray, anyelement, int) CASCADE;
DROP FUNCTION tsq_parse(search_query text) CASCADE;
DROP FUNCTION tsq_parse(config text, search_query text) CASCADE;
DROP FUNCTION tsq_parse(config regconfig, search_query text) CASCADE;
DROP FUNCTION tsq_process_tokens(tokens text[]) CASCADE;
DROP FUNCTION tsq_process_tokens(config regconfig, tokens text[]) CASCADE;
DROP FUNCTION tsq_tokenize(search_query text) CASCADE;
DROP FUNCTION tsq_tokenize_character(state tsq_state) CASCADE;
DROP FUNCTION tsq_append_current_token(state tsq_state) CASCADE;
DROP TYPE tsq_state CASCADE;
'''


def upgrade():
    conn = op.get_bind()
    metadata = sa.Metadata(bind=conn)

    op.execute(sa.DDL(expressions))

    op.add_column('comment', sa.Column('search_vector',
        TSVectorType('message_text', weights={'message_text': 'A'}),
        nullable=True))
    op.create_index('ix_comment_search_vector', 'comment', ['search_vector'],
        unique=False, postgresql_using='gin')

    op.add_column('label', sa.Column('search_vector',
        TSVectorType(
            'name', 'title', 'description',
            weights={'name': 'A', 'title': 'A', 'description': 'B'}
            ),
        nullable=True))
    op.create_index('ix_label_search_vector', 'label', ['search_vector'],
        unique=False, postgresql_using='gin')

    op.add_column('profile', sa.Column('search_vector',
        TSVectorType(
            'name', 'title', 'description',
            weights={'name': 'A', 'title': 'A', 'description': 'B'}
            ),
        nullable=True))
    op.create_index('ix_profile_search_vector', 'profile', ['search_vector'],
        unique=False, postgresql_using='gin')

    op.add_column('project', sa.Column('search_vector',
        TSVectorType(
            'name', 'title', 'description_text', 'instructions_text', 'location',
            weights={
                'name': 'A', 'title': 'A', 'description_text': 'B', 'instructions_text': 'B',
                'location': 'C'
                }
            ),
        nullable=True))
    op.create_index('ix_project_search_vector', 'project', ['search_vector'],
        unique=False, postgresql_using='gin')

    op.add_column('proposal', sa.Column('search_vector',
        TSVectorType(
            'title', 'abstract_text', 'outline_text', 'requirements_text', 'slides',
            'preview_video', 'links', 'bio',
            weights={
                'title': 'A',
                'abstract_text': 'B',
                'outline_text': 'B',
                'requirements_text': 'B',
                'slides': 'B',
                'preview_video': 'C',
                'links': 'B',
                'bio': 'B',
                }
            ),
        nullable=True))
    op.create_index('ix_proposal_search_vector', 'proposal', ['search_vector'],
        unique=False, postgresql_using='gin')

    op.add_column('session', sa.Column('search_vector',
        TSVectorType(
            'title', 'description_text', 'speaker_bio_text', 'speaker',
            weights={
                'title': 'A', 'description_text': 'B', 'speaker_bio_text': 'B', 'speaker': 'A'
                }
            ),
        nullable=True))
    op.create_index('ix_session_search_vector', 'session', ['search_vector'],
        unique=False, postgresql_using='gin')

    # Insert trigger here

    op.alter_column('comment', 'search_vector', nullable=False)
    op.alter_column('label', 'search_vector', nullable=False)
    op.alter_column('profile', 'search_vector', nullable=False)
    op.alter_column('project', 'search_vector', nullable=False)
    op.alter_column('proposal', 'search_vector', nullable=False)
    op.alter_column('session', 'search_vector', nullable=False)


def downgrade():
    conn = op.get_bind()
    metadata = sa.Metadata(bind=conn)

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

    op.execute(sa.DDL(drop_expressions))
