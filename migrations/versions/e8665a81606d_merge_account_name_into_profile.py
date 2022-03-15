# type: ignore
"""Merge account_name into profile.

Revision ID: e8665a81606d
Revises: d50c3d8e3f33
Create Date: 2020-04-15 02:24:49.259869

"""
from textwrap import dedent

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import column, table
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e8665a81606d'
down_revision = 'd50c3d8e3f33'
branch_labels = None
depends_on = None


class PROFILE_STATE:
    AUTO = 0
    PUBLIC = 1
    PRIVATE = 2


account_name = table(
    'account_name',
    column('id', UUID(as_uuid=True)),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('name', sa.Unicode(63)),
    column('user_id', sa.Integer),
    column('organization_id', sa.Integer),
    column('reserved', sa.Boolean),
)

profile = table(
    'profile',
    column('uuid', UUID(as_uuid=True)),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('name', sa.Unicode(63)),
    column('title', sa.Unicode()),
    column('user_id', sa.Integer),
    column('organization_id', sa.Integer),
    column('reserved', sa.Boolean),
    column('state', sa.Integer),
    column('description_text', sa.UnicodeText),
    column('description_html', sa.UnicodeText),
    column('legacy', sa.Boolean),
)

user = table(
    'user', column('uuid', UUID(as_uuid=True)), column('fullname', sa.Unicode())
)

organization = table(
    'organization', column('uuid', UUID(as_uuid=True)), column('title', sa.Unicode())
)


def upgrade():
    # Add search vectors and triggers to user and organization tables
    op.add_column(
        'user', sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True)
    )
    op.create_index(
        'ix_user_search_vector',
        'user',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )
    op.add_column(
        'organization', sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True)
    )
    op.create_index(
        'ix_organization_search_vector',
        'organization',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
    )

    # Update search vectors for existing data in user and organization,
    # and drop trigger in profile
    op.execute(
        sa.DDL(
            dedent(
                '''
                UPDATE "user" SET search_vector = setweight(to_tsvector('english', COALESCE(fullname, '')), 'A');
                UPDATE organization SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A');

                CREATE FUNCTION user_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.fullname, '')), 'A');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER user_search_vector_trigger BEFORE INSERT OR UPDATE ON "user"
                FOR EACH ROW EXECUTE PROCEDURE user_search_vector_update();

                CREATE FUNCTION organization_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER organization_search_vector_trigger BEFORE INSERT OR UPDATE ON organization
                FOR EACH ROW EXECUTE PROCEDURE organization_search_vector_update();

                DROP TRIGGER profile_search_vector_trigger ON profile;
                DROP FUNCTION profile_search_vector_update();
                '''
            )
        )
    )
    op.alter_column(
        'user', 'search_vector', existing_type=postgresql.TSVECTOR(), nullable=False
    )
    op.alter_column(
        'organization',
        'search_vector',
        existing_type=postgresql.TSVECTOR(),
        nullable=False,
    )

    op.add_column('profile', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('profile', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.add_column(
        'profile',
        sa.Column(
            'reserved',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('profile', 'reserved', server_default=None)
    # Add state column, make existing profiles public
    op.add_column(
        'profile',
        sa.Column(
            'state',
            sa.Integer(),
            nullable=False,
            server_default=sa.text(str(PROFILE_STATE.PUBLIC)),
        ),
    )
    op.alter_column('profile', 'state', server_default=None)
    op.create_index(op.f('ix_profile_reserved'), 'profile', ['reserved'], unique=False)
    op.create_unique_constraint('profile_user_id_key', 'profile', ['user_id'])
    op.create_unique_constraint(
        'profile_organization_id_key', 'profile', ['organization_id']
    )
    op.create_foreign_key(
        'profile_user_id_fkey',
        'profile',
        'user',
        ['user_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'profile_organization_id_fkey',
        'profile',
        'organization',
        ['organization_id'],
        ['id'],
        ondelete='SET NULL',
    )

    op.execute(
        sa.DDL(
            'CREATE UNIQUE INDEX ix_profile_name_lower ON profile (lower(name) varchar_pattern_ops);'
        )
    )

    op.drop_column('profile', 'status')
    op.drop_column('profile', 'title')

    # Update search vector and re-create trigger
    op.execute(
        sa.DDL(
            dedent(
                '''
                UPDATE profile
                SET search_vector = setweight(to_tsvector('english',COALESCE(name, '')), 'A')
                || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B');

                CREATE FUNCTION profile_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER profile_search_vector_trigger BEFORE INSERT OR UPDATE ON profile
                FOR EACH ROW EXECUTE PROCEDURE profile_search_vector_update();
                '''
            )
        )
    )

    # Update profile from account_name for existing profiles
    op.execute(
        profile.update()
        .where(profile.c.uuid == account_name.c.id)
        .values(
            {
                'name': account_name.c.name,
                'user_id': account_name.c.user_id,
                'organization_id': account_name.c.organization_id,
                'reserved': account_name.c.reserved,
            }
        )
    )
    # Insert additional profiles from account_name
    existing_profiles = sa.select([profile.c.uuid])
    account_name_data = sa.select(
        [
            account_name.c.id,
            account_name.c.created_at,
            account_name.c.updated_at,
            account_name.c.name,
            account_name.c.user_id,
            account_name.c.organization_id,
            account_name.c.reserved,
            PROFILE_STATE.AUTO,  # state
            sa.text("''"),  # description_text
            sa.text("''"),  # description_html
            sa.sql.expression.false(),  # legacy
        ]
    ).where(account_name.c.id.notin_(existing_profiles))
    op.execute(
        profile.insert().from_select(
            [
                'uuid',
                'created_at',
                'updated_at',
                'name',
                'user_id',
                'organization_id',
                'reserved',
                'state',
                'description_text',
                'description_html',
                'legacy',
            ],
            account_name_data,
        )
    )

    # Turn orphaned profiles into reserved profiles. We can't delete them because they
    # may contain user data
    op.execute(
        profile.update()
        .where(
            sa.and_(profile.c.user_id.is_(None), profile.c.organization_id.is_(None))
        )
        .values({'reserved': True})
    )

    # Add a check constraint to prevent the orphan condition from accidentally happening
    op.create_check_constraint(
        'profile_owner_check',
        'profile',
        'CASE WHEN (user_id IS NOT NULL) THEN 1 ELSE 0 END + CASE WHEN (organization_id IS NOT NULL) THEN 1 ELSE 0 END + CASE WHEN (reserved IS true) THEN 1 ELSE 0 END = 1',
    )


def downgrade():
    # Drop autogenerated profiles
    op.execute(profile.delete().where(profile.c.state == PROFILE_STATE.AUTO))

    # Drop search vector trigger
    op.execute(
        sa.DDL(
            dedent(
                '''
                DROP TRIGGER profile_search_vector_trigger ON profile;
                DROP FUNCTION profile_search_vector_update();
                '''
            )
        )
    )

    op.add_column(
        'profile',
        sa.Column(
            'title',
            sa.VARCHAR(length=250),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.alter_column('profile', 'title', server_default=None)

    # Restore profile.title from sources in user and organization tables
    op.execute(
        profile.update()
        .where(sa.and_(profile.c.user_id.isnot(None), profile.c.uuid == user.c.uuid))
        .values({'title': user.c.fullname})
    )
    op.execute(
        profile.update()
        .where(
            sa.and_(
                profile.c.organization_id.isnot(None),
                profile.c.uuid == organization.c.uuid,
            )
        )
        .values({'title': organization.c.title})
    )

    op.add_column(
        'profile',
        sa.Column(
            'status',
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column('profile', 'status', server_default=None)

    op.drop_index('ix_profile_name_lower', table_name='profile')
    op.drop_constraint('profile_owner_check', 'profile', type_='check')
    op.drop_constraint('profile_organization_id_fkey', 'profile', type_='foreignkey')
    op.drop_constraint('profile_user_id_fkey', 'profile', type_='foreignkey')
    op.drop_constraint('profile_organization_id_key', 'profile', type_='unique')
    op.drop_constraint('profile_user_id_key', 'profile', type_='unique')
    op.drop_index(op.f('ix_profile_reserved'), table_name='profile')
    op.drop_column('profile', 'state')
    op.drop_column('profile', 'reserved')
    op.drop_column('profile', 'organization_id')
    op.drop_column('profile', 'user_id')

    # Update search vector and re-create trigger
    op.execute(
        sa.DDL(
            dedent(
                '''
                UPDATE profile
                SET search_vector = setweight(to_tsvector('english',COALESCE(name, '')), 'A')
                || setweight(to_tsvector('english', COALESCE(title, '')), 'A')
                || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B');

                CREATE FUNCTION profile_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER profile_search_vector_trigger BEFORE INSERT OR UPDATE ON profile
                FOR EACH ROW EXECUTE PROCEDURE profile_search_vector_update();

                DROP TRIGGER organization_search_vector_trigger ON organization;
                DROP FUNCTION organization_search_vector_update();

                DROP TRIGGER user_search_vector_trigger ON "user";
                DROP FUNCTION user_search_vector_update();
                '''
            )
        )
    )

    op.drop_index('ix_organization_search_vector', table_name='organization')
    op.drop_column('organization', 'search_vector')
    op.drop_index('ix_user_search_vector', table_name='user')
    op.drop_column('user', 'search_vector')
