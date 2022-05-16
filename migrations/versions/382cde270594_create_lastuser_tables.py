"""Create Lastuser tables.

Revision ID: 382cde270594
Revises: 09562978e3de
Create Date: 2020-04-07 01:51:58.147168

"""

from alembic import op
from sqlalchemy_utils import UUIDType
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '382cde270594'
down_revision = '09562978e3de'
branch_labels = None
depends_on = None

upgrade_triggers = '''
CREATE OR REPLACE FUNCTION user_user_email_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    target RECORD;
BEGIN
    IF (NEW.user_email_id IS NOT NULL) THEN
        SELECT user_id INTO target FROM user_email WHERE id = NEW.user_email_id;
        IF (target.user_id != NEW.user_id) THEN
            RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$;

CREATE TRIGGER user_user_email_primary_trigger BEFORE INSERT OR UPDATE
ON user_user_email_primary
FOR EACH ROW EXECUTE PROCEDURE user_user_email_primary_validate();

CREATE OR REPLACE FUNCTION user_user_phone_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    target RECORD;
BEGIN
    IF (NEW.user_phone_id IS NOT NULL) THEN
        SELECT user_id INTO target FROM user_phone WHERE id = NEW.user_phone_id;
        IF (target.user_id != NEW.user_id) THEN
            RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$;

CREATE TRIGGER user_user_phone_primary_trigger BEFORE INSERT OR UPDATE
ON user_user_phone_primary
FOR EACH ROW EXECUTE PROCEDURE user_user_phone_primary_validate();
'''

downgrade_triggers = '''
DROP TRIGGER user_user_phone_primary_trigger ON user_user_phone_primary;
DROP FUNCTION user_user_phone_primary_validate();
DROP TRIGGER user_user_email_primary_trigger ON user_user_email_primary;
DROP FUNCTION user_user_email_primary_validate();
'''


def upgrade():
    op.create_table(
        'organization',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('owners_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.Unicode(length=80), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_table(
        'sms_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('transactionid', sa.UnicodeText(), nullable=True),
        sa.Column('message', sa.UnicodeText(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('status_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('fail_reason', sa.UnicodeText(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transactionid'),
    )
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('fullname', sa.Unicode(length=80), nullable=False),
        sa.Column('pw_hash', sa.String(length=80), nullable=True),
        sa.Column('pw_set_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('pw_expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('timezone', sa.Unicode(length=40), nullable=True),
        sa.Column('status', sa.SmallInteger(), nullable=False),
        sa.Column('avatar', sa.UnicodeText(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_table(
        'account_name',
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('name', sa.Unicode(length=63), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('reserved', sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            'CASE WHEN (user_id IS NOT NULL) THEN 1 ELSE 0 END + CASE WHEN (organization_id IS NOT NULL) THEN 1 ELSE 0 END + CASE WHEN (reserved IS true) THEN 1 ELSE 0 END = 1',
            name='account_name_owner_check',
        ),
        sa.ForeignKeyConstraint(
            ['organization_id'], ['organization.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('organization_id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(
        op.f('ix_account_name_reserved'), 'account_name', ['reserved'], unique=False
    )
    op.create_table(
        'auth_client',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.Column('confidential', sa.Boolean(), nullable=False),
        sa.Column('website', sa.UnicodeText(), nullable=False),
        sa.Column('namespace', sa.UnicodeText(), nullable=True),
        sa.Column('redirect_uri', sa.UnicodeText(), nullable=True),
        sa.Column('notification_uri', sa.UnicodeText(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('allow_any_login', sa.Boolean(), nullable=False),
        sa.Column('trusted', sa.Boolean(), nullable=False),
        sa.Column('scope', sa.UnicodeText(), nullable=True),
        sa.CheckConstraint(
            'CASE WHEN (user_id IS NOT NULL) THEN 1 ELSE 0 END + CASE WHEN (organization_id IS NOT NULL) THEN 1 ELSE 0 END = 1',
            name='auth_client_owner_check',
        ),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('namespace'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_table(
        'auth_password_reset_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reset_code', sa.String(length=44), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_auth_password_reset_request_user_id'),
        'auth_password_reset_request',
        ['user_id'],
        unique=False,
    )
    op.create_table(
        'team',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_table(
        'user_email',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.Unicode(length=254), nullable=False),
        sa.Column('md5sum', sa.String(length=32), nullable=False),
        sa.Column('domain', sa.Unicode(length=253), nullable=False),
        sa.Column('private', sa.Boolean(), nullable=False),
        sa.Column('type', sa.Unicode(length=30), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('md5sum'),
    )
    op.create_index(
        op.f('ix_user_email_domain'), 'user_email', ['domain'], unique=False
    )
    op.create_table(
        'user_email_claim',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.Unicode(length=254), nullable=True),
        sa.Column('verification_code', sa.String(length=44), nullable=False),
        sa.Column('md5sum', sa.String(length=32), nullable=False),
        sa.Column('domain', sa.Unicode(length=253), nullable=False),
        sa.Column('private', sa.Boolean(), nullable=False),
        sa.Column('type', sa.Unicode(length=30), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'email'),
    )
    op.create_index(
        op.f('ix_user_email_claim_domain'), 'user_email_claim', ['domain'], unique=False
    )
    op.create_index(
        op.f('ix_user_email_claim_email'), 'user_email_claim', ['email'], unique=False
    )
    op.create_index(
        op.f('ix_user_email_claim_md5sum'), 'user_email_claim', ['md5sum'], unique=False
    )
    op.create_table(
        'user_externalid',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service', sa.UnicodeText(), nullable=False),
        sa.Column('userid', sa.UnicodeText(), nullable=False),
        sa.Column('username', sa.UnicodeText(), nullable=True),
        sa.Column('oauth_token', sa.UnicodeText(), nullable=True),
        sa.Column('oauth_token_secret', sa.UnicodeText(), nullable=True),
        sa.Column('oauth_token_type', sa.UnicodeText(), nullable=True),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service', 'userid'),
    )
    op.create_table(
        'user_oldid',
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'user_phone',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.UnicodeText(), nullable=False),
        sa.Column('gets_text', sa.Boolean(), nullable=False),
        sa.Column('private', sa.Boolean(), nullable=False),
        sa.Column('type', sa.Unicode(length=30), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone'),
    )
    op.create_table(
        'user_phone_claim',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.UnicodeText(), nullable=False),
        sa.Column('gets_text', sa.Boolean(), nullable=False),
        sa.Column('verification_code', sa.Unicode(length=4), nullable=False),
        sa.Column('verification_attempts', sa.Integer(), nullable=False),
        sa.Column('private', sa.Boolean(), nullable=False),
        sa.Column('type', sa.Unicode(length=30), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'phone'),
    )
    op.create_index(
        op.f('ix_user_phone_claim_phone'), 'user_phone_claim', ['phone'], unique=False
    )
    op.create_table(
        'user_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ipaddr', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.UnicodeText(), nullable=False),
        sa.Column('accessed_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('sudo_enabled_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
    )
    op.create_table(
        'auth_client_credential',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('auth_client_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=22), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('secret_hash', sa.String(length=71), nullable=False),
        sa.Column('accessed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['auth_client_id'], ['auth_client.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'auth_client_team_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('auth_client_id', sa.Integer(), nullable=False),
        sa.Column('permissions', sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(['auth_client_id'], ['auth_client.id']),
        sa.ForeignKeyConstraint(['team_id'], ['team.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'auth_client_id'),
    )
    op.create_index(
        op.f('ix_auth_client_team_permissions_auth_client_id'),
        'auth_client_team_permissions',
        ['auth_client_id'],
        unique=False,
    )
    op.create_table(
        'auth_client_user_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('auth_client_id', sa.Integer(), nullable=False),
        sa.Column('permissions', sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(['auth_client_id'], ['auth_client.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'auth_client_id'),
    )
    op.create_index(
        op.f('ix_auth_client_user_permissions_auth_client_id'),
        'auth_client_user_permissions',
        ['auth_client_id'],
        unique=False,
    )
    op.create_table(
        'auth_client_user_session',
        sa.Column('auth_client_id', sa.Integer(), nullable=False),
        sa.Column('user_session_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('accessed_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['auth_client_id'], ['auth_client.id']),
        sa.ForeignKeyConstraint(['user_session_id'], ['user_session.id']),
        sa.PrimaryKeyConstraint('auth_client_id', 'user_session_id'),
    )
    op.create_table(
        'auth_code',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('auth_client_id', sa.Integer(), nullable=False),
        sa.Column('user_session_id', sa.Integer(), nullable=True),
        sa.Column('code', sa.String(length=44), nullable=False),
        sa.Column('redirect_uri', sa.UnicodeText(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('scope', sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(['auth_client_id'], ['auth_client.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['user_session_id'], ['user_session.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'auth_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_session_id', sa.Integer(), nullable=True),
        sa.Column('auth_client_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=22), nullable=False),
        sa.Column('token_type', sa.String(length=250), nullable=False),
        sa.Column('secret', sa.String(length=44), nullable=True),
        sa.Column('algorithm', sa.String(length=20), nullable=True),
        sa.Column('validity', sa.Integer(), nullable=False),
        sa.Column('refresh_token', sa.String(length=22), nullable=True),
        sa.Column('scope', sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(['auth_client_id'], ['auth_client.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['user_session_id'], ['user_session.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token'),
        sa.UniqueConstraint('token'),
        sa.UniqueConstraint('user_id', 'auth_client_id'),
        sa.UniqueConstraint('user_session_id', 'auth_client_id'),
    )
    op.create_index(
        op.f('ix_auth_token_auth_client_id'),
        'auth_token',
        ['auth_client_id'],
        unique=False,
    )
    op.create_table(
        'team_membership',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['team.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('user_id', 'team_id'),
    )
    op.create_table(
        'user_user_email_primary',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_email_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_email_id'], ['user_email.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_table(
        'user_user_phone_primary',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('user_phone_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['user_phone_id'], ['user_phone.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.add_column('comment', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'comment_user_id_fkey', 'comment', 'user', ['user_id'], ['id']
    )
    op.add_column('contact_exchange', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'contact_exchange_user_id_fkey',
        'contact_exchange',
        'user',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.add_column('participant', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'participant_user_id_fkey', 'participant', 'user', ['user_id'], ['id']
    )
    op.add_column('profile', sa.Column('admin_team_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'profile_admin_team_id_fkey',
        'profile',
        'team',
        ['admin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column('project', sa.Column('admin_team_id', sa.Integer(), nullable=True))
    op.add_column('project', sa.Column('checkin_team_id', sa.Integer(), nullable=True))
    op.add_column('project', sa.Column('review_team_id', sa.Integer(), nullable=True))
    op.add_column('project', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'project_admin_team_id_fkey',
        'project',
        'team',
        ['admin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'project_review_team_id_fkey',
        'project',
        'team',
        ['review_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'project_checkin_team_id_fkey',
        'project',
        'team',
        ['checkin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'project_user_id_fkey', 'project', 'user', ['user_id'], ['id']
    )
    op.add_column('proposal', sa.Column('speaker_id', sa.Integer(), nullable=True))
    op.add_column('proposal', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'proposal_user_id_fkey', 'proposal', 'user', ['user_id'], ['id']
    )
    op.create_foreign_key(
        'proposal_speaker_id_fkey', 'proposal', 'user', ['speaker_id'], ['id']
    )
    op.add_column('rsvp', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('rsvp_user_id_fkey', 'rsvp', 'user', ['user_id'], ['id'])
    op.add_column('saved_project', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'saved_project_user_id_fkey',
        'saved_project',
        'user',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.add_column('saved_session', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'saved_session_user_id_fkey',
        'saved_session',
        'user',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.add_column('vote', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(
        'vote_user_id_voteset_id_key', 'vote', ['user_id', 'voteset_id']
    )
    op.create_foreign_key('vote_user_id_fkey', 'vote', 'user', ['user_id'], ['id'])

    op.execute(
        sa.DDL(
            "CREATE UNIQUE INDEX ix_account_name_name_lower ON account_name (lower(name) varchar_pattern_ops);"
        )
    )
    op.execute(
        sa.DDL(
            "CREATE INDEX ix_user_fullname_lower ON \"user\" (lower(fullname) varchar_pattern_ops);"
        )
    )
    op.execute(
        sa.DDL(
            "CREATE UNIQUE INDEX ix_user_email_email_lower ON user_email (lower(email) varchar_pattern_ops);"
        )
    )
    op.execute(
        sa.DDL(
            "CREATE INDEX ix_user_externalid_username_lower ON user_externalid (lower(username) varchar_pattern_ops);"
        )
    )

    op.execute(sa.DDL(upgrade_triggers))

    print("ALERT! Import data from Lastuser before the next migration")
    print("Use `pg_dump --data-only --exclude-table=alembic_version`")


def downgrade():
    op.execute(sa.DDL(downgrade_triggers))

    op.drop_index('ix_user_externalid_username_lower', table_name='user_externalid')
    op.drop_index('ix_user_email_email_lower', table_name='user_email')
    op.drop_index('ix_user_fullname_lower', table_name='user')
    op.drop_index('ix_account_name_name_lower', table_name='account_name')

    op.drop_constraint('vote_user_id_fkey', 'vote', type_='foreignkey')
    op.drop_constraint('vote_user_id_voteset_id_key', 'vote', type_='unique')
    op.drop_column('vote', 'user_id')
    op.drop_constraint(
        'saved_session_user_id_fkey', 'saved_session', type_='foreignkey'
    )
    op.drop_column('saved_session', 'user_id')
    op.drop_constraint(
        'saved_project_user_id_fkey', 'saved_project', type_='foreignkey'
    )
    op.drop_column('saved_project', 'user_id')
    op.drop_constraint('rsvp_user_id_fkey', 'rsvp', type_='foreignkey')
    op.drop_column('rsvp', 'user_id')
    op.drop_constraint('proposal_speaker_id_fkey', 'proposal', type_='foreignkey')
    op.drop_constraint('proposal_user_id_fkey', 'proposal', type_='foreignkey')
    op.drop_column('proposal', 'user_id')
    op.drop_column('proposal', 'speaker_id')
    op.drop_constraint('project_user_id_fkey', 'project', type_='foreignkey')
    op.drop_constraint('project_checkin_team_id_fkey', 'project', type_='foreignkey')
    op.drop_constraint('project_review_team_id_fkey', 'project', type_='foreignkey')
    op.drop_constraint('project_admin_team_id_fkey', 'project', type_='foreignkey')
    op.drop_column('project', 'user_id')
    op.drop_column('project', 'review_team_id')
    op.drop_column('project', 'checkin_team_id')
    op.drop_column('project', 'admin_team_id')
    op.drop_constraint('profile_admin_team_id_fkey', 'profile', type_='foreignkey')
    op.drop_column('profile', 'admin_team_id')
    op.drop_constraint('participant_user_id_fkey', 'participant', type_='foreignkey')
    op.drop_column('participant', 'user_id')
    op.drop_constraint(
        'contact_exchange_user_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.drop_column('contact_exchange', 'user_id')
    op.drop_constraint('comment_user_id_fkey', 'comment', type_='foreignkey')
    op.drop_column('comment', 'user_id')
    op.drop_table('user_user_phone_primary')
    op.drop_table('user_user_email_primary')
    op.drop_table('team_membership')
    op.drop_index(op.f('ix_auth_token_auth_client_id'), table_name='auth_token')
    op.drop_table('auth_token')
    op.drop_table('auth_code')
    op.drop_table('auth_client_user_session')
    op.drop_index(
        op.f('ix_auth_client_user_permissions_auth_client_id'),
        table_name='auth_client_user_permissions',
    )
    op.drop_table('auth_client_user_permissions')
    op.drop_index(
        op.f('ix_auth_client_team_permissions_auth_client_id'),
        table_name='auth_client_team_permissions',
    )
    op.drop_table('auth_client_team_permissions')
    op.drop_table('auth_client_credential')
    op.drop_table('user_session')
    op.drop_index(op.f('ix_user_phone_claim_phone'), table_name='user_phone_claim')
    op.drop_table('user_phone_claim')
    op.drop_table('user_phone')
    op.drop_table('user_oldid')
    op.drop_table('user_externalid')
    op.drop_index(op.f('ix_user_email_claim_md5sum'), table_name='user_email_claim')
    op.drop_index(op.f('ix_user_email_claim_email'), table_name='user_email_claim')
    op.drop_index(op.f('ix_user_email_claim_domain'), table_name='user_email_claim')
    op.drop_table('user_email_claim')
    op.drop_index(op.f('ix_user_email_domain'), table_name='user_email')
    op.drop_table('user_email')
    op.drop_table('team')
    op.drop_index(
        op.f('ix_auth_password_reset_request_user_id'),
        table_name='auth_password_reset_request',
    )
    op.drop_table('auth_password_reset_request')
    op.drop_table('auth_client')
    op.drop_index(op.f('ix_account_name_reserved'), table_name='account_name')
    op.drop_table('account_name')
    op.drop_table('user')
    op.drop_table('sms_message')
    op.drop_table('organization')
