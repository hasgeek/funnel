# -*- coding: utf-8 -*-
"""init

Revision ID: 184ed1055383
Revises: None
Create Date: 2013-04-20 10:15:06.179822

"""

# revision identifiers, used by Alembic.
revision = '184ed1055383'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('userid', sa.String(length=22), nullable=False),
        sa.Column('fullname', sa.Unicode(length=80), nullable=False),
        sa.Column('username', sa.Unicode(length=80), nullable=True),
        sa.Column('pw_hash', sa.String(length=80), nullable=True),
        sa.Column('timezone', sa.Unicode(length=40), nullable=True),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('userid'),
        sa.UniqueConstraint('username'),
    )
    op.create_table(
        'organization',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('owners_id', sa.Integer(), nullable=True),
        sa.Column('userid', sa.String(length=22), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=True),
        sa.Column('title', sa.Unicode(length=80), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('userid'),
    )
    op.create_table(
        'smsmessage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('transaction_id', sa.Unicode(length=40), nullable=True),
        sa.Column('message', sa.UnicodeText(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('status_at', sa.DateTime(), nullable=True),
        sa.Column('fail_reason', sa.Unicode(length=25), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id'),
    )
    op.create_table(
        'client',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('org_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.Column('website', sa.Unicode(length=250), nullable=False),
        sa.Column('redirect_uri', sa.Unicode(length=250), nullable=True),
        sa.Column('notification_uri', sa.Unicode(length=250), nullable=True),
        sa.Column('iframe_uri', sa.Unicode(length=250), nullable=True),
        sa.Column('resource_uri', sa.Unicode(length=250), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('allow_any_login', sa.Boolean(), nullable=False),
        sa.Column('team_access', sa.Boolean(), nullable=False),
        sa.Column('key', sa.String(length=22), nullable=False),
        sa.Column('secret', sa.String(length=44), nullable=False),
        sa.Column('trusted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )
    op.create_table(
        'permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('org_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.Column('allusers', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'noticetype',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.Column('allusers', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'useremailclaim',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.Unicode(length=80), nullable=True),
        sa.Column('verification_code', sa.String(length=44), nullable=False),
        sa.Column('md5sum', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'useroldid',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('userid', sa.String(length=22), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('userid'),
    )
    op.create_table(
        'userphoneclaim',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.Unicode(length=80), nullable=False),
        sa.Column('gets_text', sa.Boolean(), nullable=False),
        sa.Column('verification_code', sa.Unicode(length=4), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'useremail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.Unicode(length=80), nullable=False),
        sa.Column('md5sum', sa.String(length=32), nullable=False),
        sa.Column('primary', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('md5sum'),
    )
    op.create_table(
        'userphone',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('primary', sa.Boolean(), nullable=False),
        sa.Column('phone', sa.Unicode(length=80), nullable=False),
        sa.Column('gets_text', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone'),
    )
    op.create_table(
        'team',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('userid', sa.String(length=22), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('userid'),
    )
    op.create_table(
        'userexternalid',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service', sa.String(length=20), nullable=False),
        sa.Column('userid', sa.String(length=250), nullable=False),
        sa.Column('username', sa.Unicode(length=80), nullable=True),
        sa.Column('oauth_token', sa.String(length=250), nullable=True),
        sa.Column('oauth_token_secret', sa.String(length=250), nullable=True),
        sa.Column('oauth_token_type', sa.String(length=250), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service', 'userid'),
    )
    op.create_table(
        'passwordresetrequest',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reset_code', sa.String(length=44), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'userflashmessage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('category', sa.Unicode(length=20), nullable=False),
        sa.Column('message', sa.Unicode(length=250), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'authcode',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=44), nullable=False),
        sa.Column('scope', sa.Unicode(length=250), nullable=False),
        sa.Column('redirect_uri', sa.Unicode(length=1024), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'team_membership',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['team.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint(),
    )
    op.create_table(
        'userclientpermissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('permissions', sa.Unicode(length=250), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'client_id'),
    )
    op.create_table(
        'authtoken',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=22), nullable=False),
        sa.Column('token_type', sa.String(length=250), nullable=False),
        sa.Column('secret', sa.String(length=44), nullable=True),
        sa.Column('algorithm', sa.String(length=20), nullable=True),
        sa.Column('scope', sa.Unicode(length=250), nullable=False),
        sa.Column('validity', sa.Integer(), nullable=False),
        sa.Column('refresh_token', sa.String(length=22), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['client.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token'),
        sa.UniqueConstraint('token'),
        sa.UniqueConstraint('user_id', 'client_id'),
    )
    op.create_table(
        'teamclientpermissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('permissions', sa.Unicode(length=250), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.id']),
        sa.ForeignKeyConstraint(['team_id'], ['team.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'client_id'),
    )
    op.create_table(
        'resource',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=20), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.Column('siteresource', sa.Boolean(), nullable=False),
        sa.Column('trusted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'clientteamaccess',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('access_level', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['client.id']),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'resourceaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=20), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(['resource_id'], ['resource.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'resource_id'),
    )
    op.create_foreign_key(
        "fk_organization_owners_id", "organization", "team", ['owners_id'], ['id']
    )
    op.create_foreign_key("fk_team_org_id", "team", "organization", ['org_id'], ['id'])


def downgrade():
    op.drop_table('resourceaction')
    op.drop_table('clientteamaccess')
    op.drop_table('resource')
    op.drop_table('teamclientpermissions')
    op.drop_table('authtoken')
    op.drop_table('userclientpermissions')
    op.drop_table('team_membership')
    op.drop_table('authcode')
    op.drop_table('userflashmessage')
    op.drop_table('passwordresetrequest')
    op.drop_table('userexternalid')
    op.drop_table('team')
    op.drop_table('userphone')
    op.drop_table('useremail')
    op.drop_table('userphoneclaim')
    op.drop_table('useroldid')
    op.drop_table('useremailclaim')
    op.drop_table('noticetype')
    op.drop_table('permission')
    op.drop_table('client')
    op.drop_table('smsmessage')
    op.drop_table('organization')
    op.drop_table('user')
