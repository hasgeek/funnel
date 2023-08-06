"""Account merges user, organization and profile.

Revision ID: 331a4250aa4b
Revises: c794b4a3a696
Create Date: 2023-05-08 13:10:17.607431

"""

from dataclasses import dataclass
from textwrap import dedent
from typing import List, Optional, Tuple, Union
from typing_extensions import Literal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '331a4250aa4b'
down_revision: str = 'c794b4a3a696'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


class AccountType:
    USER = 'U'
    ORG = 'O'
    PLACEHOLDER = 'P'


class ProfileState:
    AUTO = 1
    PUBLIC = 2
    PRIVATE = 3


@dataclass
class Rn:
    """Rename pair."""

    #: Old name
    current_name: str
    #: New name
    future_name: Optional[str] = None
    #: Symbol type
    symbol: Optional[
        Literal[
            # These symbols need a table
            'column',
            'constraint',
            'trigger',
            # These do not need a table
            'table',
            'index',
            'function',
            'sequence',
        ]
    ] = None
    #: Optional namespace (table for columns and constraints, not required for others)
    table_name: Optional[str] = None
    #: Old table name (autoset by Rtable)
    old_table_name: Optional[str] = None

    def _do(self, current_name: str, future_name: str) -> None:
        """Internal function for performing the operation."""
        qtable = sa.quoted_name(self.table_name, None) if self.table_name else None
        qold = sa.quoted_name(current_name, None)
        qnew = sa.quoted_name(future_name, None)
        if self.symbol == 'column':
            assert self.table_name is not None  # nosec B101
            op.alter_column(self.table_name, current_name, new_column_name=future_name)
        elif self.symbol == 'constraint':
            assert self.table_name is not None  # nosec B101
            op.execute(f'ALTER TABLE {qtable} RENAME CONSTRAINT {qold} TO {qnew}')
        elif self.symbol == 'trigger':
            assert self.table_name is not None  # nosec B101
            op.execute(f'ALTER TRIGGER {qold} ON {qtable} RENAME TO {qnew}')
        elif self.symbol == 'sequence':
            op.execute(f'ALTER SEQUENCE {qold} RENAME TO {qnew}')
        elif self.symbol == 'table':
            op.rename_table(current_name, future_name)
        elif self.symbol == 'index':
            op.execute(f'ALTER INDEX {qold} RENAME TO {qnew}')
        elif self.symbol == 'function':
            op.execute(f'ALTER FUNCTION {qold} RENAME TO {qnew}')
        elif self.symbol == 'function':
            op.execute(f'ALTER FUNCTION {qold} RENAME TO {qnew}')
        else:
            raise TypeError("Unknown symbol type in {self!r}")

    def _format_names(self) -> Tuple[str, Optional[str]]:
        """Format old and new named using the table name."""
        old = self.current_name
        new = self.future_name
        if self.old_table_name and self.table_name and '{}' in old:
            old = old.format(self.old_table_name)
            if new is None:
                new = self.current_name.format(self.table_name)
            elif '{}' in new:
                new = new.format(self.table_name)
        elif self.table_name and new is not None and '{}' in new:
            new = new.format(self.table_name)
        return old, new

    def upgrade(self) -> None:
        """Do the rename."""
        old, new = self._format_names()
        if new is not None and new != old:
            self._do(old, new)

    def downgrade(self) -> None:
        """Undo the rename."""
        old, new = self._format_names()
        if new is not None and new != old:
            self._do(new, old)  # Rename in reverse


@dataclass
class Rtable(Rn):
    """Rename a table and/or its contents and related entities."""

    sequences: Optional[List[Rn]] = None
    columns: Optional[List[Rn]] = None
    constraints: Optional[List[Rn]] = None
    indexes: Optional[List[Rn]] = None
    triggers: Optional[List[Rn]] = None
    functions: Optional[List[Rn]] = None

    def __post_init__(self):
        """Set table and symbol type in lists."""
        self.symbol = 'table'
        for symbol, source in [
            ('sequence', self.sequences),
            ('column', self.columns),
            ('constraint', self.constraints),
            ('index', self.indexes),
            ('trigger', self.triggers),
            ('function', self.functions),
        ]:
            if source:
                for rn in source:
                    # If renaming this table, use `self.new` for the new name
                    # If not renaming (new is None), use old name from `self.old`
                    rn.table_name = self.future_name or self.current_name
                    rn.old_table_name = self.current_name
                    rn.symbol = symbol

    def upgrade(self) -> None:
        """Do the rename."""
        super().upgrade()
        for source in (
            self.sequences,
            self.columns,
            self.constraints,
            self.indexes,
            self.triggers,
            self.functions,
        ):
            if source:
                for rn in source:
                    rn.upgrade()

    def downgrade(self) -> None:
        """Undo rename."""
        for source in (
            self.functions,
            self.triggers,
            self.indexes,
            self.constraints,
            self.columns,
            self.sequences,
        ):
            if source:
                for rn in source[::-1]:
                    rn.downgrade()

        super().downgrade()


account = sa.table(
    'account',
    sa.column('type', sa.CHAR(1)),
    sa.column('created_at', sa.TIMESTAMP(timezone=True)),
    sa.column('updated_at', sa.TIMESTAMP(timezone=True)),
    sa.column('joined_at', sa.TIMESTAMP(timezone=True)),
    sa.column('name', sa.Unicode()),
    sa.column('title', sa.Unicode()),
    sa.column('bio', sa.Unicode()),
    sa.column('description_text', sa.UnicodeText()),
    sa.column('description_html', sa.UnicodeText()),
    sa.column('website', sa.Unicode()),
    sa.column('logo_url', sa.Unicode()),
    sa.column('banner_image_url', sa.Unicode()),
    sa.column('is_protected', sa.Boolean()),
    sa.column('is_verified', sa.Boolean()),
    sa.column('revisionid', sa.Integer()),
)

# All renames
renames = [
    Rtable(
        'user',
        'account',
        sequences=[Rn('{}_id_seq')],
        columns=[Rn('fullname', 'title')],
        constraints=[Rn('{}_pkey'), Rn('{}_state_check'), Rn('{}_uuid_key')],
        indexes=[
            Rn('ix_{}_fullname_lower', 'ix_{}_title_lower'),
            Rn('ix_{}_search_vector'),
        ],
    ),
    Rtable(
        'organization_membership',
        'account_admin_membership',
        columns=[Rn('user_id', 'member_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_record_type_check'),
            Rn('{}_granted_by_id_fkey'),
            Rn('{}_organization_id_fkey'),
            Rn('{}_revoked_by_id_fkey'),
            Rn('{}_user_id_fkey', '{}_member_id_fkey'),
        ],
        indexes=[
            Rn('ix_{}_active'),
            Rn('ix_{}_user_id', 'ix_{}_member_id'),
        ],
    ),
    Rtable(
        'user_email',
        'account_email',
        sequences=[Rn('{}_id_seq')],
        columns=[Rn('user_id', 'account_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_email_address_id_key'),
            Rn('{}_email_address_id_fkey'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
    ),
    Rtable(
        'user_email_claim',
        'account_email_claim',
        sequences=[Rn('{}_id_seq')],
        columns=[Rn('user_id', 'account_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_user_id_email_address_id_key', '{}_account_id_email_address_id_key'),
            Rn('{}_email_address_id_fkey'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
        indexes=[Rn('ix_{}_email_address_id')],
    ),
    Rtable(
        'user_phone',
        'account_phone',
        sequences=[Rn('{}_id_seq')],
        columns=[Rn('user_id', 'account_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_phone_number_id_key'),
            Rn('{}_phone_number_id_fkey'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
    ),
    Rtable(
        'user_externalid',
        'account_externalid',
        sequences=[Rn('{}_id_seq')],
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_pkey'), Rn('{}_service_userid_key'), Rn('{}_user_id_fkey')],
        indexes=[Rn('ix_{}_oauth_expires_at'), Rn('ix_{}_username_lower')],
    ),
    Rtable(
        'user_oldid',
        'account_oldid',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_pkey'), Rn('{}_user_id_fkey', '{}_account_id_fkey')],
    ),
    Rtable(
        'user_user_email_primary',
        'account_account_email_primary',
        columns=[Rn('user_id', 'account_id'), Rn('user_email_id', 'account_email_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_user_email_id_fkey', '{}_account_email_id_fkey'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
        triggers=[Rn('{}_trigger')],
        functions=[Rn('{}_validate')],
    ),
    Rtable(
        'user_user_phone_primary',
        'account_account_phone_primary',
        columns=[Rn('user_id', 'account_id'), Rn('user_phone_id', 'account_phone_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_user_phone_id_fkey', '{}_account_phone_id_fkey'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
        triggers=[Rn('{}_trigger')],
        functions=[Rn('{}_validate')],
    ),
    Rtable(
        'auth_client',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('auth_client_user_id_fkey', 'auth_client_account_id_fkey')],
    ),
    Rtable(
        'auth_client_user_permissions',
        'auth_client_permissions',
        sequences=[Rn('{}_id_seq')],
        columns=[Rn('user_id', 'account_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_user_id_auth_client_id_key', '{}_account_id_auth_client_id_key'),
            Rn('{}_auth_client_id_fkey'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
        indexes=[Rn('ix_{}_auth_client_id')],
    ),
    Rtable(
        'auth_code',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_account_id_fkey')],
    ),
    Rtable(
        'auth_token',
        columns=[Rn('user_id', 'account_id')],
        constraints=[
            Rn('{}_user_id_auth_client_id_key', '{}_account_id_auth_client_id_key'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
    ),
    Rtable(
        'commentset_membership',
        columns=[Rn('user_id', 'member_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_member_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_member_id')],
    ),
    Rtable(
        'project',
        columns=[Rn('user_id', 'created_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_created_by_id_fkey')],
    ),
    Rtable(
        'project_crew_membership',
        columns=[Rn('user_id', 'member_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_member_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_member_id')],
    ),
    Rtable(
        'proposal',
        columns=[Rn('user_id', 'created_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_created_by_id_fkey')],
    ),
    Rtable(
        'proposal_membership',
        columns=[Rn('user_id', 'member_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_member_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_member_id')],
    ),
    Rtable(
        'site_membership',
        columns=[Rn('user_id', 'member_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_member_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_member_id')],
    ),
    Rtable(
        'team_membership',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_account_id_fkey')],
    ),
    Rtable(
        'update',
        columns=[Rn('user_id', 'created_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_created_by_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_created_by_id')],
    ),
]


def upgrade(engine_name='') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name='') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""

    # This upgrade has multiple parts:
    # 1. Rename user -> account and various other tables and reference columns
    # 2. Add extra columns to account table
    # 3. Merge profile and organization data into account (preserving UUID)
    # 4. Replace organization_id and profile_id fkeys with account_id
    #    (use UUID as interim and just change fkey target?)
    # 5. Drop organization and profile models

    op.execute(
        sa.text(
            dedent(
                '''
                DROP TRIGGER user_search_vector_trigger ON "user";
                DROP FUNCTION user_search_vector_update();
                '''
            )
        )
    )

    for rn in renames:
        rn.upgrade()

    # Add new columns and indexes to 'account' table
    with op.batch_alter_table('account') as batch_op:
        batch_op.add_column(
            sa.Column('type', sa.CHAR(1), nullable=False, server_default='U')
        )
        batch_op.add_column(sa.Column('name', sa.Unicode(63), nullable=True))
        batch_op.add_column(
            sa.Column(
                'joined_at',
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
        )
        batch_op.add_column(
            sa.Column(
                'profile_state',
                sa.SmallInteger(),
                nullable=False,
                server_default=sa.text(str(ProfileState.AUTO)),
            ),
        )
        batch_op.add_column(
            sa.Column(
                'tagline',
                sa.Unicode(),
                sa.CheckConstraint("tagline <> ''"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                'description_text', sa.UnicodeText(), nullable=False, server_default=''
            )
        )
        batch_op.add_column(
            sa.Column(
                'description_html', sa.UnicodeText(), nullable=False, server_default=''
            )
        )
        batch_op.add_column(
            sa.Column(
                'website',
                sa.Unicode,
                sa.CheckConstraint("website <> ''"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                'logo_url',
                sa.Unicode,
                sa.CheckConstraint("logo_url <> ''"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                'banner_image_url',
                sa.Unicode,
                sa.CheckConstraint("banner_image_url <> ''"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                'is_protected', sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.add_column(
            sa.Column(
                'is_verified', sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.add_column(
            sa.Column(
                'revisionid', sa.Integer(), nullable=False, server_default=sa.text('1')
            )
        )
        batch_op.add_column(
            sa.Column('name_vector', postgresql.TSVECTOR(), nullable=True)
        )
    # Drop server_default
    with op.batch_alter_table('account') as batch_op:
        batch_op.alter_column('joined_at', server_default=None)
        batch_op.alter_column('profile_state', server_default=None)
        batch_op.alter_column('type', server_default=None)
        batch_op.alter_column('description_text', server_default=None)
        batch_op.alter_column('description_html', server_default=None)
        batch_op.alter_column('is_protected', server_default=None)
        batch_op.alter_column('is_verified', server_default=None)
        batch_op.alter_column('revisionid', server_default=None)

    op.create_index(
        'ix_account_name_vector',
        'account',
        ['name_vector'],
        unique=False,
        postgresql_using='gin',
    )

    op.create_index(
        op.f('ix_account_is_verified'), 'account', ['is_verified'], unique=False
    )
    op.create_index(
        'ix_account_name_lower',
        'account',
        [sa.text('lower(name)')],
        unique=True,
        postgresql_ops={'name_lower': 'varchar_pattern_ops'},
    )

    # Recreate account search_vector function and trigger, and add name_vector handlers
    op.execute(
        sa.text(
            dedent(
                '''
                CREATE FUNCTION account_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.tagline, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER account_search_vector_trigger BEFORE INSERT OR UPDATE OF title, name, tagline, description_text
                ON account FOR EACH ROW EXECUTE PROCEDURE account_search_vector_update();

                UPDATE account SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(name, '')), 'A') || setweight(to_tsvector('english', COALESCE(tagline, '')), 'B') || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B');

                CREATE FUNCTION account_name_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.name_vector := to_tsvector('simple', COALESCE(NEW.title, '')) || to_tsvector('simple', COALESCE(NEW.name, ''));
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER account_name_vector_trigger BEFORE INSERT OR UPDATE OF title, name
                ON account FOR EACH ROW EXECUTE PROCEDURE account_name_vector_update();

                UPDATE account SET name_vector = to_tsvector('simple', COALESCE(title, '')) || to_tsvector('simple', COALESCE(name, ''));
                '''
            )
        )
    )
    op.execute(account.update().values(joined_at=account.c.created_at))
    op.alter_column('account', 'name_vector', nullable=False)

    # TODO:
    # account_admin_membership.organization_id -> account_id (after merge)
    # ix_account_admin_membership_active column change to account_id
    # auth_client.organization_id to be dropped, replaced with account_id value
    # Project.profile_id -> account_id
    # ProjectRedirect.profile_id -> account_id
    # ProjectSponsorMembership.profile_id -> member_id (account; or drop model entirely)
    # ix_project_sponsor_membership_active column change
    # ProposalSponsorMembership.profile_id -> member_id (or drop model entirely)
    # Team.organization_id -> account_id


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.execute(
        sa.text(
            dedent(
                '''
                DROP TRIGGER account_name_vector_trigger ON account;
                DROP FUNCTION account_name_vector_update();
                DROP TRIGGER account_search_vector_trigger ON account;
                DROP FUNCTION account_search_vector_update();
                '''
            )
        )
    )

    op.drop_index(op.f('ix_account_name_lower'), table_name='account')
    op.drop_index(op.f('ix_account_is_verified'), table_name='account')
    op.drop_index(op.f('ix_account_name_vector'), table_name='account')
    with op.batch_alter_table('account') as batch_op:
        batch_op.drop_column('name_vector')
        batch_op.drop_column('description_html')
        batch_op.drop_column('description_text')
        batch_op.drop_column('tagline')
        batch_op.drop_column('profile_state')
        batch_op.drop_column('name')
        batch_op.drop_column('joined_at')
        batch_op.drop_column('type')

    for rename in renames[::-1]:
        rename.downgrade()

    op.execute(
        sa.text(
            dedent(
                '''
                CREATE FUNCTION user_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.fullname, '')), 'A');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER user_search_vector_trigger BEFORE INSERT OR UPDATE
                ON "user" FOR EACH ROW EXECUTE PROCEDURE user_search_vector_update();

                UPDATE "user" SET search_vector = setweight(to_tsvector('english', COALESCE(fullname, '')), 'A');
                '''
            )
        )
    )
