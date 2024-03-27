"""Post model.

Revision ID: a1ab7bd78649
Revises: b6d0edac3e20
Create Date: 2020-07-03 10:57:39.988762

"""

from textwrap import dedent

import sqlalchemy as sa
from alembic import op
from sqlalchemy_utils import TSVectorType

# revision identifiers, used by Alembic.
revision = 'a1ab7bd78649'
down_revision = 'e4f17fe2cce8'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        'post',
        sa.Column('visibility', sa.SmallInteger(), nullable=False),
        sa.Column('state', sa.SmallInteger(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('message_text', sa.UnicodeText(), nullable=False),
        sa.Column('message_html', sa.UnicodeText(), nullable=False),
        sa.Column('pinned', sa.Boolean(), nullable=False),
        sa.Column('published_by_id', sa.Integer(), nullable=True),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('deleted_by_id', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('edited_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('voteset_id', sa.Integer(), nullable=False),
        sa.Column('commentset_id', sa.Integer(), nullable=False),
        sa.Column('search_vector', TSVectorType(), nullable=False),
        sa.Column('uuid', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            'CASE WHEN (profile_id IS NOT NULL) THEN 1 ELSE 0 END + CASE WHEN (project_id IS NOT NULL) THEN 1 ELSE 0 END = 1',
            name='post_owner_check',
        ),
        sa.ForeignKeyConstraint(['commentset_id'], ['commentset.id']),
        sa.ForeignKeyConstraint(['deleted_by_id'], ['user.id']),
        sa.ForeignKeyConstraint(['profile_id'], ['profile.id']),
        sa.ForeignKeyConstraint(['project_id'], ['project.id']),
        sa.ForeignKeyConstraint(['published_by_id'], ['user.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['voteset_id'], ['voteset.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_index(
        op.f('ix_post_deleted_by_id'), 'post', ['deleted_by_id'], unique=False
    )
    op.create_index(op.f('ix_post_profile_id'), 'post', ['profile_id'], unique=False)
    op.create_index(op.f('ix_post_project_id'), 'post', ['project_id'], unique=False)
    op.create_index(
        op.f('ix_post_published_by_id'), 'post', ['published_by_id'], unique=False
    )
    op.create_index(op.f('ix_post_user_id'), 'post', ['user_id'], unique=False)

    op.execute(
        sa.text(
            dedent(
                '''
        CREATE FUNCTION post_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.body_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER post_search_vector_trigger BEFORE INSERT OR UPDATE ON post
        FOR EACH ROW EXECUTE PROCEDURE post_search_vector_update();
                '''
            )
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            dedent(
                '''
        DROP TRIGGER post_search_vector_trigger ON post;
        DROP FUNCTION post_search_vector_update();
        '''
            )
        )
    )
    op.drop_index(op.f('ix_post_user_id'), table_name='post')
    op.drop_index(op.f('ix_post_published_by_id'), table_name='post')
    op.drop_index(op.f('ix_post_project_id'), table_name='post')
    op.drop_index(op.f('ix_post_profile_id'), table_name='post')
    op.drop_index(op.f('ix_post_deleted_by_id'), table_name='post')
    op.drop_table('post')
