"""Account merges user, organization and profile.

Revision ID: 331a4250aa4b
Revises: d5b374c9e589
Create Date: 2023-05-08 13:10:17.607431

"""

from dataclasses import dataclass
from textwrap import dedent
from typing import List, Optional, Tuple, Union
from typing_extensions import Literal

import sqlalchemy as sa
from alembic import op
from rich import get_console
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '331a4250aa4b'
down_revision: str = 'd5b374c9e589'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


class AccountType:
    """Account type flag."""

    USER = 'U'
    ORG = 'O'
    PLACEHOLDER = 'P'


class ProfileState:
    """Profile public-visibility state."""

    AUTO = 1
    PUBLIC = 2
    PRIVATE = 3


class AccountAndOrgState:
    """Account and Organization (shared) state."""

    ACTIVE = 1
    SUSPENDED = 2


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

notification_recipient = sa.table(
    'notification_recipient', sa.column('role', sa.Unicode())
)

account_membership = sa.table(
    'account_membership',
    sa.column('account_id', sa.Integer()),
    sa.column('organization_id', sa.Integer()),
)

auth_client = sa.table(
    'auth_client',
    sa.column('account_id', sa.Integer()),
    sa.column('organization_id', sa.Integer()),
)

project = sa.table(
    'project',
    sa.column('account_id', sa.Integer()),
    sa.column('profile_id', sa.Integer()),
)

project_redirect = sa.table(
    'project_redirect',
    sa.column('account_id', sa.Integer()),
    sa.column('profile_id', sa.Integer()),
    sa.column('name', sa.Unicode()),
    sa.column('project_id', sa.Integer()),
)

project_sponsor_membership = sa.table(
    'project_sponsor_membership',
    sa.column('member_id', sa.Integer()),
    sa.column('profile_id', sa.Integer()),
)

proposal_sponsor_membership = sa.table(
    'proposal_sponsor_membership',
    sa.column('member_id', sa.Integer()),
    sa.column('profile_id', sa.Integer()),
)

team = sa.table(
    'team',
    sa.column('account_id', sa.Integer()),
    sa.column('organization_id', sa.Integer()),
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
        'profile',
        columns=[Rn('user_id', 'account_id')],
        constraints=[
            Rn('{}_user_id_key', '{}_account_id_key'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
    ),
    Rtable(
        'organization_membership',
        'account_membership',
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
        columns=[
            Rn('user_id', 'account_id'),
            Rn('user_session_id', 'login_session_id'),
        ],
        constraints=[
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
            Rn('{}_user_session_id_fkey', '{}_login_session_id_fkey'),
        ],
    ),
    Rtable(
        'auth_token',
        columns=[
            Rn('user_id', 'account_id'),
            Rn('user_session_id', 'login_session_id'),
        ],
        constraints=[
            Rn('{}_user_id_auth_client_id_key', '{}_account_id_auth_client_id_key'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
            Rn(
                '{}_user_session_id_auth_client_id_key',
                '{}_login_session_id_auth_client_id_key',
            ),
            Rn('{}_user_session_id_fkey', '{}_user_session_id_fkey'),
        ],
    ),
    Rtable(
        'comment',
        columns=[Rn('user_id', 'posted_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_posted_by_id_fkey')],
    ),
    Rtable(
        'commentset_membership',
        columns=[Rn('user_id', 'member_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_member_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_member_id')],
    ),
    Rtable(
        'comment_moderator_report',
        columns=[Rn('user_id', 'reported_by_id')],
        constraints=[
            Rn('{}_user_id_fkey', '{}_reported_by_id_fkey'),
            Rn(
                '{}_user_id_notification_type_key',
                '{}_account_id_notification_type_key',
            ),
        ],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_reported_by_id')],
    ),
    Rtable(
        'notification_preferences',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_account_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_account_id')],
    ),
    Rtable(
        'notification',
        columns=[Rn('user_id', 'created_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_created_by_id_fkey')],
    ),
    Rtable(
        'project',
        columns=[Rn('user_id', 'created_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_created_by_id_fkey')],
    ),
    Rtable(
        'project_crew_membership',
        'project_membership',
        columns=[Rn('user_id', 'member_id')],
        constraints=[Rn('{}_pkey'), Rn('{}_user_id_fkey', '{}_member_id_fkey')],
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
        'rsvp',
        columns=[Rn('user_id', 'participant_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_participant_id_fkey')],
    ),
    Rtable(
        'saved_project',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_account_id_fkey')],
    ),
    Rtable(
        'saved_session',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_account_id_fkey')],
    ),
    Rtable(
        'shortlink',
        columns=[Rn('user_id', 'created_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_created_by_id_fkey')],
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
        'ticket_participant',
        columns=[Rn('user_id', 'participant_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_participant_id_fkey')],
    ),
    Rtable(
        'update',
        columns=[Rn('user_id', 'created_by_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_created_by_id_fkey')],
        indexes=[Rn('ix_{}_user_id', 'ix_{}_created_by_id')],
    ),
    Rtable(
        'user_notification',
        'notification_recipient',
        columns=[Rn('user_id', 'recipient_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_user_id_fkey', '{}_recipient_id_fkey'),
            Rn('{}_eventid_notification_id_fkey'),
        ],
        indexes=[Rn('ix_{}_revoked_at'), Rn('ix_{}_rollupid')],
    ),
    Rtable(
        'user_session',
        'login_session',
        sequences=[Rn('{}_id_seq')],
        columns=[Rn('user_id', 'account_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_uuid_key'),
            Rn('{}_user_id_fkey', '{}_account_id_fkey'),
        ],
    ),
    Rtable(
        'auth_client_user_session',
        'auth_client_login_session',
        columns=[Rn('user_session_id', 'login_session_id')],
        constraints=[
            Rn('{}_pkey'),
            Rn('{}_auth_client_id_fkey'),
            Rn('{}_user_session_id_fkey', '{}_login_session_id_fkey'),
        ],
    ),
    Rtable(
        'contact_exchange',
        columns=[Rn('user_id', 'account_id')],
        constraints=[Rn('{}_user_id_fkey', '{}_account_id_fkey')],
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

    console = get_console()

    with console.status("Dropping obsolete search_vector function and trigger"):
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

    with console.status("Resetting user_id_seq"):
        conn = op.get_bind()
        last_user_id = conn.scalar(
            sa.select(sa.func.max(sa.table('user', sa.column('id', sa.Integer())).c.id))
        )
        conn.execute(sa.select(sa.func.setval('user_id_seq', last_user_id)))

    with console.status("Renaming user -> account"):
        for rn in renames:
            rn.upgrade()

    # Add new columns and indexes to 'account' table
    with console.status("Adding columns to account"), op.batch_alter_table(
        'account'
    ) as batch_op:
        batch_op.alter_column('search_vector', nullable=True)
        batch_op.add_column(
            sa.Column(
                'type', sa.CHAR(1), nullable=False, server_default=AccountType.USER
            )
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
        batch_op.alter_column('profile_state', server_default=None)
        batch_op.alter_column('type', server_default=None)
        batch_op.alter_column('description_text', server_default=None)
        batch_op.alter_column('description_html', server_default=None)
        batch_op.alter_column('is_protected', server_default=None)
        batch_op.alter_column('is_verified', server_default=None)
        batch_op.alter_column('revisionid', server_default=None)

    with console.status("Recreating indexes"):
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

    # Fix profiles which have a UUID not matching the account UUID, a data integrity
    # error. This operation cannot be reversed as the original UUID is lost.
    with console.status("Fixing profile.uuid where it differs from account.uuid"):
        op.execute(
            profile.update()
            .values(uuid=account.c.uuid)
            .where(
                profile.c.account_id == account.c.id, profile.c.uuid != account.c.uuid
            )
        )

    # Insert organization data into account
    with console.status("Copying organization data into account table"):
        op.execute(
            account.insert().from_select(  # type: ignore[arg-type]
                [
                    'type',
                    'uuid',
                    'created_at',
                    'updated_at',
                    'title',
                    'state',
                    'profile_state',
                    'auto_timezone',
                    'auto_locale',
                    'description_text',
                    'description_html',
                    'is_protected',
                    'is_verified',
                    'revisionid',
                ],
                sa.select(
                    sa.text(f"'{AccountType.ORG}'"),
                    organization.c.uuid,
                    organization.c.created_at,
                    organization.c.updated_at,
                    organization.c.title,
                    organization.c.state,
                    sa.text(str(ProfileState.AUTO)),
                    sa.true().label('auto_timezone'),
                    sa.true().label('auto_locale'),
                    sa.text("''"),
                    sa.text("''"),
                    sa.false().label('is_protected'),
                    sa.false().label('is_verified'),
                    sa.text('1'),
                ).order_by(organization.c.created_at),
            )
        )

    with console.status("Setting account.joined_at = account.created_at"):
        op.execute(account.update().values(joined_at=account.c.created_at))

    # Merge profile data into account
    with console.status("Copying profile data into account table"):
        op.execute(
            account.update()
            .values(
                updated_at=sa.func.greatest(account.c.updated_at, profile.c.updated_at),
                name=profile.c.name,
                profile_state=profile.c.state,
                tagline=sa.case(
                    (profile.c.tagline != '', profile.c.tagline), else_=sa.null()
                ),
                description_text=profile.c.description_text,
                description_html=profile.c.description_html,
                website=sa.case(
                    (profile.c.website != '', profile.c.website), else_=sa.null()
                ),
                logo_url=sa.case(
                    (profile.c.logo_url != '', profile.c.logo_url), else_=sa.null()
                ),
                banner_image_url=sa.case(
                    (profile.c.banner_image_url != '', profile.c.banner_image_url),
                    else_=sa.null(),
                ),
                is_protected=profile.c.is_protected,
                is_verified=profile.c.is_verified,
                revisionid=1,
            )
            .where(profile.c.uuid == account.c.uuid, profile.c.reserved.is_(False))
        )
        op.execute(
            account.insert().from_select(  # type: ignore[arg-type]
                [
                    'type',
                    'uuid',
                    'created_at',
                    'updated_at',
                    'name',
                    'title',
                    'state',
                    'profile_state',
                    'tagline',
                    'description_text',
                    'description_html',
                    'website',
                    'logo_url',
                    'banner_image_url',
                    'is_protected',
                    'is_verified',
                    'auto_timezone',
                    'auto_locale',
                    'revisionid',
                ],
                sa.select(
                    sa.text(f"'{AccountType.PLACEHOLDER}'"),
                    profile.c.uuid,
                    profile.c.created_at,
                    profile.c.updated_at,
                    profile.c.name,
                    sa.text("''"),
                    sa.text(str(AccountAndOrgState.ACTIVE)),
                    profile.c.state,
                    sa.case(
                        (profile.c.tagline != '', profile.c.tagline), else_=sa.null()
                    ),
                    profile.c.description_text,
                    profile.c.description_html,
                    sa.case(
                        (profile.c.website != '', profile.c.website), else_=sa.null()
                    ),
                    sa.case(
                        (profile.c.logo_url != '', profile.c.logo_url), else_=sa.null()
                    ),
                    sa.case(
                        (profile.c.banner_image_url != '', profile.c.banner_image_url),
                        else_=sa.null(),
                    ),
                    profile.c.is_protected,
                    profile.c.is_verified,
                    sa.true().label('auto_timezone'),
                    sa.true().label('auto_locale'),
                    sa.text('1'),
                )
                .where(profile.c.reserved.is_(True))
                .order_by(profile.c.created_at),
            )
        )

    with console.status("Updating notifications"):
        op.execute(
            notification_recipient.update()
            .values(role='account_admin')
            .where(notification_recipient.c.role == 'profile_admin')
        )
        op.execute(
            notification_recipient.update()
            .values(role='member')
            .where(notification_recipient.c.role == 'subject')
        )

    with console.status("Updating account_membership"):
        op.add_column(
            'account_membership',
            sa.Column(
                'account_id',
                sa.Integer(),
                sa.ForeignKey(
                    'account.id',
                    name='account_membership_account_id_fkey',
                    ondelete='CASCADE',
                ),
                nullable=True,
            ),
        )
        op.execute(
            account_membership.update()
            .values(account_id=account.c.id)
            .where(
                account_membership.c.organization_id == organization.c.id,
                account.c.uuid == organization.c.uuid,
            )
        )
        op.alter_column('account_membership', 'account_id', nullable=False)
        op.drop_constraint(
            'account_membership_organization_id_fkey',
            'account_membership',
            type_='foreignkey',
        )
        op.drop_index('ix_account_membership_active')
        op.create_index(
            'ix_account_membership_active',
            'account_membership',
            ['account_id', 'member_id'],
            unique=True,
            postgresql_where='revoked_at IS NULL',
        )
        op.drop_column('account_membership', 'organization_id')

    with console.status("Updating auth_client"):
        op.execute(
            auth_client.update()
            .values(organization_id=None, account_id=account.c.id)
            .where(
                auth_client.c.organization_id.isnot(None),
                auth_client.c.organization_id == organization.c.id,
                organization.c.uuid == account.c.uuid,
            )
        )
        op.drop_constraint('auth_client_owner_check', 'auth_client', type_='check')
        op.drop_constraint(
            'auth_client_organization_id_fkey', 'auth_client', type_='foreignkey'
        )
        op.drop_column('auth_client', 'organization_id')

    with console.status("Updating project"):
        op.add_column(
            'project',
            sa.Column(
                'account_id',
                sa.Integer(),
                sa.ForeignKey('account.id', name='project_account_id_fkey'),
                nullable=True,
            ),
        )
        op.execute(
            project.update()
            .values(account_id=account.c.id)
            .where(
                project.c.profile_id == profile.c.id,
                profile.c.uuid == account.c.uuid,
            )
        )
        op.alter_column('project', 'account_id', nullable=False)
        op.create_unique_constraint(
            'project_account_id_name_key', 'project', ['account_id', 'name']
        )
        op.drop_constraint('project_profile_id_name_key', 'project', type_='unique')
        op.drop_constraint('project_profile_id_fkey', 'project', type_='foreignkey')
        op.drop_column('project', 'profile_id')

    with console.status("Updating project_redirect"):
        op.add_column(
            'project_redirect',
            sa.Column(
                'account_id',
                sa.Integer(),
                sa.ForeignKey('account.id', name='project_redirect_account_id_fkey'),
                nullable=True,
            ),
        )
        op.execute(
            project_redirect.update()
            .values(account_id=account.c.id)
            .where(
                project_redirect.c.profile_id == profile.c.id,
                account.c.uuid == profile.c.uuid,
            )
        )
        op.alter_column('project_redirect', 'account_id', nullable=False)
        op.drop_constraint('project_redirect_pkey', 'project_redirect', type_='primary')
        op.create_primary_key(
            'project_redirect_pkey', 'project_redirect', ['account_id', 'name']
        )
        op.drop_constraint(
            'project_redirect_profile_id_fkey', 'project_redirect', type_='foreignkey'
        )
        op.drop_column('project_redirect', 'profile_id')

    with console.status("Updating project_sponsor_membership"):
        op.add_column(
            'project_sponsor_membership',
            sa.Column(
                'member_id',
                sa.Integer(),
                sa.ForeignKey(
                    'account.id',
                    name='project_sponsor_membership_member_id_fkey',
                    ondelete='CASCADE',
                ),
                nullable=True,
            ),
        )
        op.execute(
            project_sponsor_membership.update()
            .values(member_id=account.c.id)
            .where(
                project_sponsor_membership.c.profile_id == profile.c.id,
                account.c.uuid == profile.c.uuid,
            )
        )
        op.alter_column('project_sponsor_membership', 'member_id', nullable=False)
        op.drop_constraint(
            'project_sponsor_membership_profile_id_fkey',
            'project_sponsor_membership',
            type_='foreignkey',
        )
        op.drop_index('ix_project_sponsor_membership_active')
        op.create_index(
            'ix_project_sponsor_membership_active',
            'project_sponsor_membership',
            ['project_id', 'member_id'],
            unique=True,
            postgresql_where='revoked_at IS NULL',
        )
        op.drop_column('project_sponsor_membership', 'profile_id')

    with console.status("Updating proposal_sponsor_membership"):
        op.add_column(
            'proposal_sponsor_membership',
            sa.Column(
                'member_id',
                sa.Integer(),
                sa.ForeignKey(
                    'account.id',
                    name='proposal_sponsor_membership_member_id_fkey',
                    ondelete='CASCADE',
                ),
                nullable=True,
            ),
        )
        op.execute(
            proposal_sponsor_membership.update()
            .values(member_id=account.c.id)
            .where(
                proposal_sponsor_membership.c.profile_id == profile.c.id,
                account.c.uuid == profile.c.uuid,
            )
        )
        op.alter_column('proposal_sponsor_membership', 'member_id', nullable=False)
        op.drop_constraint(
            'proposal_sponsor_membership_profile_id_fkey',
            'proposal_sponsor_membership',
            type_='foreignkey',
        )
        op.drop_index('ix_proposal_sponsor_membership_active')
        op.create_index(
            'ix_proposal_sponsor_membership_active',
            'proposal_sponsor_membership',
            ['proposal_id', 'member_id'],
            unique=True,
            postgresql_where='revoked_at IS NULL',
        )
        op.drop_column('proposal_sponsor_membership', 'profile_id')

    with console.status("Updating team"):
        op.add_column(
            'team',
            sa.Column(
                'account_id',
                sa.Integer(),
                sa.ForeignKey('account.id', name='team_account_id_fkey'),
                nullable=True,
            ),
        )
        op.execute(
            team.update()
            .values(account_id=account.c.id)
            .where(
                team.c.organization_id == organization.c.id,
                account.c.uuid == organization.c.uuid,
            )
        )
        op.alter_column('team', 'account_id', nullable=False)
        op.drop_constraint('team_organization_id_fkey', 'team', type_='foreignkey')
        op.drop_column('team', 'organization_id')
        op.create_index('ix_team_account_id', 'team', ['account_id'], unique=False)

    # Recreate account search_vector function and trigger, and add name_vector handlers
    with console.status("Rebuilding search vectors"):
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
        op.alter_column('account', 'search_vector', nullable=False)
        op.alter_column('account', 'name_vector', nullable=False)
        op.create_index(
            'ix_account_name_vector',
            'account',
            ['name_vector'],
            unique=False,
            postgresql_using='gin',
        )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    console = get_console()

    with console.status("Dropping mismatched search vector functions and triggers"):
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

    with console.status("Updating team"):
        op.add_column(
            'team',
            sa.Column(
                'organization_id',
                sa.Integer(),
                sa.ForeignKey('organization.id', name='team_organization_id_fkey'),
                nullable=True,
            ),
        )
        op.execute(
            team.update()
            .values(organization_id=organization.c.id)
            .where(
                team.c.account_id == account.c.id,
                account.c.uuid == organization.c.uuid,
            )
        )
        op.alter_column('team', 'organization_id', nullable=False)
        op.drop_constraint('team_account_id_fkey', 'team', type_='foreignkey')
        op.drop_index('ix_team_account_id', 'team')
        op.drop_column('team', 'account_id')

    with console.status("Updating proposal_sponsor_membership"):
        op.add_column(
            'proposal_sponsor_membership',
            sa.Column(
                'profile_id',
                sa.Integer(),
                sa.ForeignKey(
                    'profile.id',
                    name='proposal_sponsor_membership_profile_id_fkey',
                    ondelete='CASCADE',
                ),
                nullable=True,
            ),
        )
        op.execute(
            proposal_sponsor_membership.update()
            .values(profile_id=profile.c.id)
            .where(
                proposal_sponsor_membership.c.member_id == account.c.id,
                account.c.uuid == profile.c.uuid,
            )
        )
        op.alter_column('proposal_sponsor_membership', 'profile_id', nullable=False)
        op.create_index(
            'ix_proposal_sponsor_membership_profile_id',
            'proposal_sponsor_membership',
            ['profile_id'],
            unique=False,
        )

        op.drop_constraint(
            'proposal_sponsor_membership_member_id_fkey',
            'proposal_sponsor_membership',
            type_='foreignkey',
        )
        op.drop_index('ix_proposal_sponsor_membership_active')
        op.create_index(
            'ix_proposal_sponsor_membership_active',
            'proposal_sponsor_membership',
            ['proposal_id', 'profile_id'],
            unique=True,
            postgresql_where='revoked_at IS NULL',
        )
        op.drop_column('proposal_sponsor_membership', 'member_id')

    with console.status("Updating project_sponsor_membership"):
        op.add_column(
            'project_sponsor_membership',
            sa.Column(
                'profile_id',
                sa.Integer(),
                sa.ForeignKey(
                    'profile.id',
                    name='project_sponsor_membership_profile_id_fkey',
                    ondelete='CASCADE',
                ),
                nullable=True,
            ),
        )
        op.execute(
            project_sponsor_membership.update()
            .values(profile_id=profile.c.id)
            .where(
                project_sponsor_membership.c.member_id == account.c.id,
                account.c.uuid == profile.c.uuid,
            )
        )
        op.alter_column('project_sponsor_membership', 'profile_id', nullable=False)
        op.create_index(
            'ix_project_sponsor_membership_profile_id',
            'project_sponsor_membership',
            ['profile_id'],
            unique=False,
        )

        op.drop_constraint(
            'project_sponsor_membership_member_id_fkey',
            'project_sponsor_membership',
            type_='foreignkey',
        )
        op.drop_index('ix_project_sponsor_membership_active')
        op.create_index(
            'ix_project_sponsor_membership_active',
            'project_sponsor_membership',
            ['project_id', 'profile_id'],
            unique=True,
            postgresql_where='revoked_at IS NULL',
        )
        op.drop_column('project_sponsor_membership', 'member_id')

    with console.status("Updating project_redirect"):
        op.add_column(
            'project_redirect',
            sa.Column(
                'profile_id',
                sa.Integer(),
                sa.ForeignKey('profile.id', name='project_redirect_profile_id_fkey'),
                nullable=True,
            ),
        )
        op.execute(
            project_redirect.update()
            .values(profile_id=profile.c.id)
            .where(
                project_redirect.c.account_id == account.c.id,
                account.c.uuid == profile.c.uuid,
            )
        )
        op.alter_column('project_redirect', 'profile_id', nullable=False)
        op.drop_constraint('project_redirect_pkey', 'project_redirect', type_='primary')
        op.create_primary_key(
            'project_redirect_pkey', 'project_redirect', ['profile_id', 'name']
        )
        op.drop_constraint(
            'project_redirect_account_id_fkey', 'project_redirect', type_='foreignkey'
        )
        op.drop_column('project_redirect', 'account_id')

    with console.status("Updating project"):
        op.add_column(
            'project',
            sa.Column(
                'profile_id',
                sa.Integer(),
                sa.ForeignKey('profile.id', name='project_profile_id_fkey'),
                nullable=True,
            ),
        )
        op.execute(
            project.update()
            .values(profile_id=profile.c.id)
            .where(
                project.c.account_id == account.c.id,
                profile.c.uuid == account.c.uuid,
            )
        )
        op.alter_column('project', 'profile_id', nullable=False)
        op.create_unique_constraint(
            'project_profile_id_name_key', 'project', ['profile_id', 'name']
        )
        op.drop_constraint('project_account_id_name_key', 'project', type_='unique')
        op.drop_constraint('project_account_id_fkey', 'project', type_='foreignkey')
        op.drop_column('project', 'account_id')

    with console.status("Updating auth_client"):
        op.add_column(
            'auth_client',
            sa.Column(
                'organization_id',
                sa.Integer(),
                sa.ForeignKey(
                    'organization.id', name='auth_client_organization_id_fkey'
                ),
                nullable=True,
            ),
        )
        op.create_check_constraint(
            'auth_client_owner_check',
            'auth_client',
            'CASE WHEN (account_id IS NOT NULL) THEN 1 ELSE 0 END'
            ' + CASE WHEN (organization_id IS NOT NULL) THEN 1 ELSE 0 END'
            ' = 1',
        )
        op.execute(
            auth_client.update()
            .values(account_id=None, organization_id=organization.c.id)
            .where(
                auth_client.c.account_id == account.c.id,
                organization.c.uuid == account.c.uuid,
            )
        )

    with console.status("Updating account_membership"):
        op.add_column(
            'account_membership',
            sa.Column(
                'organization_id',
                sa.Integer(),
                sa.ForeignKey(
                    'organization.id',
                    name='account_membership_organization_id_fkey',
                    ondelete='CASCADE',
                ),
                nullable=True,
            ),
        )
        op.execute(
            account_membership.update()
            .values(organization_id=organization.c.id)
            .where(
                account_membership.c.account_id == account.c.id,
                account.c.uuid == organization.c.uuid,
            )
        )
        op.alter_column('account_membership', 'organization_id', nullable=False)
        op.drop_constraint(
            'account_membership_account_id_fkey',
            'account_membership',
            type_='foreignkey',
        )
        op.drop_index('ix_account_membership_active', 'account_membership')
        op.create_index(
            'ix_account_membership_active',
            'account_membership',
            ['organization_id', 'member_id'],
            unique=True,
            postgresql_where='revoked_at IS NULL',
        )
        op.drop_column('account_membership', 'account_id')

    with console.status("Updating notifications"):
        op.execute(
            notification_recipient.update()
            .values(role='profile_admin')
            .where(notification_recipient.c.role == 'account_admin')
        )
        op.execute(
            notification_recipient.update()
            .values(role='subject')
            .where(notification_recipient.c.role == 'member')
        )

    # Delete all non-user rows from account
    with console.status("Dropping all non-user data from account table (slow!)"):
        op.execute(
            account.delete().where(  # type: ignore[arg-type]
                account.c.type != AccountType.USER
            )
        )

    with console.status("Dropping new columns and indexes on account"):
        op.drop_index(op.f('ix_account_name_lower'), table_name='account')
        op.drop_index(op.f('ix_account_is_verified'), table_name='account')
        op.drop_index(op.f('ix_account_name_vector'), table_name='account')
        with op.batch_alter_table('account') as batch_op:
            batch_op.drop_column('revisionid')
            batch_op.drop_column('name_vector')
            batch_op.drop_column('logo_url')
            batch_op.drop_column('banner_image_url')
            batch_op.drop_column('is_protected')
            batch_op.drop_column('is_verified')
            batch_op.drop_column('website')
            batch_op.drop_column('description_html')
            batch_op.drop_column('description_text')
            batch_op.drop_column('tagline')
            batch_op.drop_column('profile_state')
            batch_op.drop_column('name')
            batch_op.drop_column('joined_at')
            batch_op.drop_column('type')

    with console.status("Renaming account -> user"):
        for rename in renames[::-1]:
            rename.downgrade()

    with console.status("Rebuilding search vectors"):
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

    with console.status("Resetting user_id_seq"):
        conn = op.get_bind()
        last_user_id = conn.scalar(
            sa.select(sa.func.max(sa.table('user', sa.column('id', sa.Integer())).c.id))
        )
        conn.execute(sa.select(sa.func.setval('user_id_seq', last_user_id)))
