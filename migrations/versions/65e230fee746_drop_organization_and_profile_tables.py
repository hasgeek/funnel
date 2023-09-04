"""Drop organization and profile tables.

Revision ID: 65e230fee746
Revises: 331a4250aa4b
Create Date: 2023-09-01 09:51:20.572077

"""

from textwrap import dedent
from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '65e230fee746'
down_revision: str = '331a4250aa4b'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


class AccountType:
    """Account type flag."""

    USER = 'U'
    ORG = 'O'
    PLACEHOLDER = 'P'


account = sa.table(
    'account',
    sa.column('id', sa.Integer()),
    sa.column('uuid', sa.Uuid()),
    sa.column('type', sa.CHAR(1)),
    sa.column('created_at', sa.TIMESTAMP(timezone=True)),
    sa.column('updated_at', sa.TIMESTAMP(timezone=True)),
    sa.column('joined_at', sa.TIMESTAMP(timezone=True)),
    sa.column('state', sa.SmallInteger()),
    sa.column('profile_state', sa.SmallInteger()),
    sa.column('name', sa.Unicode()),
    sa.column('title', sa.Unicode()),
    sa.column('tagline', sa.Unicode()),
    sa.column('description_text', sa.UnicodeText()),
    sa.column('description_html', sa.UnicodeText()),
    sa.column('website', sa.Unicode()),
    sa.column('logo_url', sa.Unicode()),
    sa.column('banner_image_url', sa.Unicode()),
    sa.column('is_protected', sa.Boolean()),
    sa.column('is_verified', sa.Boolean()),
    sa.column('revisionid', sa.Integer()),
    sa.column('auto_timezone', sa.Boolean()),
    sa.column('auto_locale', sa.Boolean()),
)

profile = sa.table(
    'profile',
    sa.column('id', sa.Integer()),
    sa.column('uuid', sa.Uuid()),
    sa.column('created_at', sa.TIMESTAMP(timezone=True)),
    sa.column('updated_at', sa.TIMESTAMP(timezone=True)),
    sa.column('state', sa.Integer()),
    sa.column('account_id', sa.Integer()),
    sa.column('organization_id', sa.Integer()),
    sa.column('reserved', sa.Boolean()),
    sa.column('name', sa.Unicode()),
    sa.column('tagline', sa.Unicode()),
    sa.column('description_text', sa.Unicode()),
    sa.column('description_html', sa.Unicode()),
    sa.column('logo_url', sa.Unicode()),
    sa.column('banner_image_url', sa.Unicode()),
    sa.column('website', sa.Unicode()),
    sa.column('is_protected', sa.Boolean()),
    sa.column('is_verified', sa.Boolean()),
    sa.column('revisionid', sa.Integer()),
)

organization = sa.table(
    'organization',
    sa.column('id', sa.Integer()),
    sa.column('uuid', sa.Uuid()),
    sa.column('created_at', sa.TIMESTAMP(timezone=True)),
    sa.column('updated_at', sa.TIMESTAMP(timezone=True)),
    sa.column('title', sa.Integer()),
    sa.column('state', sa.SmallInteger()),
)


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""
    op.execute(
        sa.text(
            '''
            DROP TRIGGER profile_search_vector_trigger ON profile;
            DROP FUNCTION profile_search_vector_update();
            '''
        )
    )
    with op.batch_alter_table('profile', schema=None) as batch_op:
        batch_op.drop_index('ix_profile_is_verified')
        batch_op.drop_index('ix_profile_name_lower')
        batch_op.drop_index('ix_profile_reserved')
        batch_op.drop_index('ix_profile_search_vector', postgresql_using='gin')
        batch_op.drop_constraint('profile_name_check', type_='check')
        batch_op.drop_constraint('profile_state_check', type_='check')
        batch_op.drop_constraint('profile_account_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('profile_organization_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('profile_account_id_key', type_='unique')
        batch_op.drop_constraint('profile_name_key', type_='unique')
        batch_op.drop_constraint('profile_organization_id_key', type_='unique')
        batch_op.drop_constraint('profile_uuid_key', type_='unique')
    op.drop_table('profile')

    op.execute(
        sa.text(
            '''
            DROP TRIGGER organization_search_vector_trigger ON organization;
            DROP FUNCTION organization_search_vector_update();
            '''
        )
    )
    with op.batch_alter_table('organization', schema=None) as batch_op:
        batch_op.drop_index('ix_organization_search_vector', postgresql_using='gin')
        batch_op.drop_constraint('organization_uuid_key', type_='unique')
        batch_op.drop_constraint('organization_state_check', type_='check')
    op.drop_table('organization')


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.create_table(
        'organization',
        sa.Column(
            'id',
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column('uuid', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('title', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column(
            'search_vector', postgresql.TSVECTOR(), autoincrement=False, nullable=False
        ),
        sa.Column('state', sa.SMALLINT(), autoincrement=False, nullable=False),
        sa.CheckConstraint(
            'state = ANY (ARRAY[1, 2])', name='organization_state_check'
        ),
        sa.PrimaryKeyConstraint('id', name='organization_pkey'),
        sa.UniqueConstraint('uuid', name='organization_uuid_key'),
        postgresql_ignore_search_path=False,
    )
    with op.batch_alter_table('organization', schema=None) as batch_op:
        batch_op.create_index(
            'ix_organization_search_vector',
            ['search_vector'],
            unique=False,
            postgresql_using='gin',
        )
    op.execute(
        sa.text(
            dedent(
                '''
            CREATE FUNCTION organization_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := setweight(to_tsvector('english',
                COALESCE(NEW.title, '')), 'A');
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER organization_search_vector_trigger
            BEFORE INSERT OR UPDATE ON organization
            FOR EACH ROW EXECUTE PROCEDURE organization_search_vector_update();
            '''
            )
        )
    )
    # TODO: Populate organization
    op.execute(
        organization.insert().from_select(  # type: ignore[arg-type]
            [
                'uuid',
                'created_at',
                'updated_at',
                'title',
                'state',
            ],
            sa.select(
                account.c.uuid,
                account.c.created_at,
                account.c.updated_at,
                account.c.title,
                account.c.state,
            )
            .where(account.c.type == AccountType.ORG)
            .order_by(account.c.created_at),
        )
    )

    op.create_table(
        'profile',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('description_text', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('description_html', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=63), autoincrement=False, nullable=False),
        sa.Column('logo_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('uuid', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            'search_vector', postgresql.TSVECTOR(), autoincrement=False, nullable=False
        ),
        sa.Column('account_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('organization_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('reserved', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('state', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('banner_image_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('website', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('is_protected', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('is_verified', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('tagline', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('revisionid', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.CheckConstraint("name::text <> ''::text", name='profile_name_check'),
        sa.CheckConstraint(
            '(\nCASE\n    WHEN account_id IS NOT NULL THEN 1\n    ELSE 0\nEND +\nCASE\n    WHEN organization_id IS NOT NULL THEN 1\n    ELSE 0\nEND +\nCASE\n    WHEN reserved IS TRUE THEN 1\n    ELSE 0\nEND) = 1',
            name='profile_owner_check',
        ),
        sa.CheckConstraint('state = ANY (ARRAY[1, 2, 3])', name='profile_state_check'),
        sa.ForeignKeyConstraint(
            ['account_id'],
            ['account.id'],
            name='profile_account_id_fkey',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organization.id'],
            name='profile_organization_id_fkey',
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id', name='profile_pkey'),
        sa.UniqueConstraint('account_id', name='profile_account_id_key'),
        sa.UniqueConstraint('name', name='profile_name_key'),
        sa.UniqueConstraint('organization_id', name='profile_organization_id_key'),
        sa.UniqueConstraint('uuid', name='profile_uuid_key'),
    )
    with op.batch_alter_table('profile', schema=None) as batch_op:
        batch_op.create_index(
            'ix_profile_search_vector',
            ['search_vector'],
            unique=False,
            postgresql_using='gin',
        )
        batch_op.create_index('ix_profile_reserved', ['reserved'], unique=False)
        batch_op.create_index(
            'ix_profile_name_lower',
            [sa.text('lower(name)')],  # type: ignore[list-item]
            unique=False,
        )
        batch_op.create_index('ix_profile_is_verified', ['is_verified'], unique=False)
    op.execute(
        sa.text(
            dedent(
                '''
                CREATE FUNCTION profile_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english',
                    COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english',
                    COALESCE(NEW.description_text, '')), 'B');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER profile_search_vector_trigger
                BEFORE INSERT OR UPDATE ON profile
                FOR EACH ROW EXECUTE PROCEDURE profile_search_vector_update();
                '''
            )
        )
    )
    # Copy user profiles
    op.execute(
        profile.insert().from_select(  # type: ignore[arg-type]
            [
                'account_id',
                'organization_id',
                'reserved',
                'uuid',
                'created_at',
                'updated_at',
                'name',
                'state',
                'tagline',
                'description_text',
                'description_html',
                'website',
                'logo_url',
                'banner_image_url',
                'is_protected',
                'is_verified',
                'revisionid',
            ],
            sa.select(
                account.c.id,
                sa.null(),
                sa.false(),
                account.c.uuid,
                account.c.created_at,
                account.c.updated_at,
                account.c.name,
                account.c.profile_state,
                account.c.tagline,
                account.c.description_text,
                account.c.description_html,
                account.c.website,
                account.c.logo_url,
                account.c.banner_image_url,
                account.c.is_protected,
                account.c.is_verified,
                account.c.revisionid,
            )
            .where(account.c.type == AccountType.USER, account.c.name.isnot(None))
            .order_by(account.c.created_at),
        )
    )
    # Copy org profiles
    op.execute(
        profile.insert().from_select(  # type: ignore[arg-type]
            [
                'account_id',
                'organization_id',
                'reserved',
                'uuid',
                'created_at',
                'updated_at',
                'name',
                'state',
                'tagline',
                'description_text',
                'description_html',
                'website',
                'logo_url',
                'banner_image_url',
                'is_protected',
                'is_verified',
                'revisionid',
            ],
            sa.select(
                sa.null(),
                organization.c.id,
                sa.false(),
                account.c.uuid,
                account.c.created_at,
                account.c.updated_at,
                account.c.name,
                account.c.profile_state,
                account.c.tagline,
                account.c.description_text,
                account.c.description_html,
                account.c.website,
                account.c.logo_url,
                account.c.banner_image_url,
                account.c.is_protected,
                account.c.is_verified,
                account.c.revisionid,
            )
            .where(
                account.c.type == AccountType.ORG,
                account.c.name.isnot(None),
                organization.c.uuid == account.c.uuid,
            )
            .order_by(account.c.created_at),
        )
    )
    # Copy reserved (placeholder) profiles
    op.execute(
        profile.insert().from_select(  # type: ignore[arg-type]
            [
                'account_id',
                'organization_id',
                'reserved',
                'uuid',
                'created_at',
                'updated_at',
                'name',
                'state',
                'tagline',
                'description_text',
                'description_html',
                'website',
                'logo_url',
                'banner_image_url',
                'is_protected',
                'is_verified',
                'revisionid',
            ],
            sa.select(
                sa.null(),
                sa.null(),
                sa.true(),
                account.c.uuid,
                account.c.created_at,
                account.c.updated_at,
                account.c.name,
                account.c.profile_state,
                account.c.tagline,
                account.c.description_text,
                account.c.description_html,
                account.c.website,
                account.c.logo_url,
                account.c.banner_image_url,
                account.c.is_protected,
                account.c.is_verified,
                account.c.revisionid,
            )
            .where(
                account.c.type == AccountType.PLACEHOLDER, account.c.name.isnot(None)
            )
            .order_by(account.c.created_at),
        )
    )
