"""OAuth2 client app models."""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from hashlib import blake2b, sha256
from typing import cast, overload

from sqlalchemy.orm import attribute_keyed_dict, load_only
from sqlalchemy.orm.query import Query as QueryBaseClass
from werkzeug.utils import cached_property

from baseframe import _
from coaster.sqlalchemy import with_roles
from coaster.utils import buid as make_buid, newsecret, require_one_of, utcnow

from . import (
    BaseMixin,
    DynamicMapped,
    Mapped,
    Model,
    Query,
    UuidMixin,
    db,
    declarative_mixin,
    declared_attr,
    relationship,
    sa,
    sa_orm,
)
from .account import Account, Team
from .helpers import reopen
from .login_session import LoginSession, auth_client_login_session

__all__ = [
    'AuthCode',
    'AuthToken',
    'AuthClient',
    'AuthClientCredential',
    'AuthClientTeamPermissions',
    'AuthClientPermissions',
]


@declarative_mixin
class ScopeMixin:
    """Mixin for models that define an access scope."""

    __scope_null_allowed__ = False

    @declared_attr
    @classmethod
    def _scope(cls) -> Mapped[str]:
        """Database column for storing scopes as a space-separated string."""
        return sa_orm.mapped_column(
            'scope', sa.UnicodeText, nullable=cls.__scope_null_allowed__
        )

    @property
    def scope(self) -> Iterable[str]:
        """Represent scope column as a container of strings."""
        if not self._scope:
            return ()
        return tuple(sorted(self._scope.split()))

    @scope.setter
    def scope(self, value: str | Iterable | None) -> None:
        if value is None:
            if self.__scope_null_allowed__:
                self._scope = None
                return
            raise ValueError("Scope cannot be None")
        if isinstance(value, str):
            value = value.split()
        self._scope = ' '.join(sorted(t.strip() for t in value if t))
        if not self._scope and self.__scope_null_allowed__:
            self._scope = None

    def add_scope(self, additional: str | Iterable) -> None:
        """Add additional items to the scope."""
        if isinstance(additional, str):
            additional = [additional]
        self.scope = set(self.scope).union(set(additional))


class AuthClient(ScopeMixin, UuidMixin, BaseMixin, Model):
    """OAuth client application."""

    __tablename__ = 'auth_client'
    __scope_null_allowed__ = True
    #: Account that owns this client
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False
    )
    account: Mapped[Account] = with_roles(
        relationship(back_populates='clients'),
        read={'all'},
        write={'owner'},
        grants_via={None: {'owner': 'owner', 'admin': 'admin'}},
    )
    #: Human-readable title
    title: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(250), nullable=False),
        read={'all'},
        write={'owner'},
    )
    #: Long description
    description: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.UnicodeText, nullable=False, default=''),
        read={'all'},
        write={'owner'},
    )
    #: Confidential or public client? Public has no secret key
    confidential: Mapped[bool] = with_roles(
        sa_orm.mapped_column(sa.Boolean, nullable=False), read={'all'}, write={'owner'}
    )
    #: Website
    website: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.UnicodeText, nullable=False),  # FIXME: Use UrlType
        read={'all'},
        write={'owner'},
    )
    #: Redirect URIs (one or more)
    _redirect_uris: Mapped[str | None] = sa_orm.mapped_column(
        'redirect_uri', sa.UnicodeText, nullable=True, default=''
    )
    #: Back-end notification URI (TODO: deprecated, needs better architecture)
    notification_uri: Mapped[str | None] = with_roles(  # FIXME: Use UrlType
        sa_orm.mapped_column(sa.UnicodeText, nullable=True, default=''), rw={'owner'}
    )
    #: Active flag
    active: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, nullable=False, default=True
    )
    #: Allow anyone to login to this app?
    allow_any_login: Mapped[bool] = with_roles(
        sa_orm.mapped_column(sa.Boolean, nullable=False, default=True),
        read={'all'},
        write={'owner'},
    )
    #: Trusted flag: trusted clients are authorized to access user data
    #: without user consent, but the user must still login and identify themself.
    #: When a single provider provides multiple services, each can be declared
    #: as a trusted client to provide single sign-in across the services.
    #: However, resources in the scope column (via ScopeMixin) are granted for
    #: any arbitrary user without explicit user authorization.
    trusted: Mapped[bool] = with_roles(
        sa_orm.mapped_column(sa.Boolean, nullable=False, default=False), read={'all'}
    )

    # --- Backrefs

    login_sessions: DynamicMapped[LoginSession] = relationship(
        lazy='dynamic',
        secondary=auth_client_login_session,
        back_populates='auth_clients',
    )
    credentials: Mapped[dict[str, AuthClientCredential]] = relationship(
        collection_class=attribute_keyed_dict('name'), back_populates='auth_client'
    )
    authcodes: DynamicMapped[AuthCode] = relationship(
        lazy='dynamic', back_populates='auth_client'
    )
    authtokens: DynamicMapped[AuthToken] = relationship(
        lazy='dynamic', back_populates='auth_client'
    )
    account_permissions: Mapped[list[AuthClientPermissions]] = relationship(
        back_populates='auth_client'
    )
    team_permissions: Mapped[list[AuthClientTeamPermissions]] = relationship(
        back_populates='auth_client'
    )

    __roles__ = {
        'all': {
            'read': {'urls'},
            'call': {'url_for'},
        }
    }

    def __repr__(self) -> str:
        """Represent :class:`AuthClient` as a string."""
        return f'<AuthClient "{self.title}" {self.buid}>'

    def secret_is(self, candidate: str, name: str) -> bool:
        """Check if the provided client secret is valid."""
        credential = self.credentials[name]
        return credential.secret_is(candidate)

    @property
    def redirect_uris(self) -> tuple[str, ...]:
        """Return redirect URIs as a sequence."""
        return tuple(self._redirect_uris.split()) if self._redirect_uris else ()

    @redirect_uris.setter
    def redirect_uris(self, value: Iterable[str]) -> None:
        """Set redirect URIs from a sequence, storing internally as lines of text."""
        self._redirect_uris = '\r\n'.join(value)

    with_roles(redirect_uris, rw={'owner'})

    @property
    def redirect_uri(self) -> str | None:
        """Return the first redirect URI, if present."""
        uris = self.redirect_uris  # Assign to local var to avoid splitting twice
        if uris:
            return uris[0]
        return None

    def host_matches(self, url: str) -> bool:
        """Return if the provided host matches one of the redirect URIs."""
        netloc = urllib.parse.urlsplit(url or '').netloc
        if netloc:
            return netloc in (
                urllib.parse.urlsplit(r).netloc
                for r in (self.redirect_uris + (self.website,))
            )
        return False

    def owner_is(self, account: Account | None) -> bool:
        """Test if the provided account is an owner of this client."""
        # Legacy method for ownership test
        return account is not None and 'owner' in self.roles_for(account)

    def authtoken_for(
        self, account: Account | None, login_session: LoginSession | None = None
    ) -> AuthToken | None:
        """
        Return the auth token for this account and client.

        Only works for confidential clients.
        """
        if self.confidential:
            if account is None:
                raise ValueError("Account not provided")
            return AuthToken.get_for(auth_client=self, account=account)
        if login_session and login_session.account == account:
            return AuthToken.get_for(auth_client=self, login_session=login_session)
        return None

    def allow_access_for(self, actor: Account) -> bool:
        """Test if access is allowed for this user as per the auth client settings."""
        if self.allow_any_login:
            return True
        if self.account:
            if AuthClientPermissions.get(self, actor):
                return True
        else:
            if AuthClientTeamPermissions.all_for(self, actor).notempty():
                return True
        return False

    @classmethod
    def get(cls, buid: str) -> AuthClient | None:
        """
        Return a AuthClient identified by its client buid or namespace.

        Only returns active clients.

        :param str buid: AuthClient buid to lookup
        """
        return cls.query.filter(cls.buid == buid, cls.active.is_(True)).one_or_none()

    @classmethod
    def all_for(cls, account: Account | None) -> Query[AuthClient]:
        """Return all clients, optionally all clients owned by the specified account."""
        if account is None:
            return cls.query.order_by(cls.title)
        return cls.query.filter(
            sa.or_(
                cls.account == account,
                cls.account_id.in_(account.organizations_as_owner_ids()),
            )
        ).order_by(cls.title)


class AuthClientCredential(BaseMixin, Model):
    """
    AuthClient key and secret hash.

    This uses unsalted Blake2 (64-bit) instead of a salted hash or a more secure hash
    like bcrypt because:

    1. Secrets are random and unique before hashing. Salting is only beneficial when
       the secrets may be reused.
    2. Unlike user passwords, client secrets are used often, up to many times per
       minute. The hash needs to be fast (MD5 or SHA) and reasonably safe from collision
       attacks (eliminating MD5, SHA0 and SHA1). Blake2 is the fastest available
       candidate meeting this criteria, replacing the previous choice of SHA256. Blake3
       is too new at this time, but is an upgrade candidate.
    3. To allow for a different hash to be used in future, hashes are stored
       prefixed with the hash name and digest size, currently 'blake2b$32$'. This code
       will transparently upgrade from the previous 'sha256$' on successful auth.
    """

    __tablename__ = 'auth_client_credential'
    auth_client_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('auth_client.id'), nullable=False
    )
    auth_client: Mapped[AuthClient] = with_roles(
        relationship(back_populates='credentials'),
        grants_via={None: {'owner'}},
    )

    #: OAuth client key
    name: Mapped[str] = sa_orm.mapped_column(
        sa.String(22), nullable=False, unique=True, default=make_buid
    )
    #: User description for this credential
    title: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(250), nullable=False, default=''
    )
    #: OAuth client secret, hashed
    secret_hash: Mapped[str] = sa_orm.mapped_column(sa.Unicode, nullable=False)
    #: When was this credential last used for an API call?
    accessed_at: Mapped[datetime | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f'<AuthClientCredential {self.name} {self.title!r}>'

    def secret_is(self, candidate: str | None, upgrade_hash: bool = False) -> bool:
        """Test if the candidate secret matches."""
        if not candidate:
            return False
        if self.secret_hash.startswith('blake2b$32$'):
            return (
                self.secret_hash
                == 'blake2b$32$'
                + blake2b(candidate.encode(), digest_size=32).hexdigest()
            )
        # Older credentials, before the switch to Blake2b:
        if self.secret_hash.startswith('sha256$'):
            matches = (
                self.secret_hash == 'sha256$' + sha256(candidate.encode()).hexdigest()
            )
            if matches and upgrade_hash:
                self.secret_hash = (
                    'blake2b$32$'
                    + blake2b(candidate.encode(), digest_size=32).hexdigest()
                )
            return matches
        return False

    @classmethod
    def get(cls, name: str) -> AuthClientCredential | None:
        """Get a client credential by its key name."""
        return cls.query.filter(cls.name == name).one_or_none()

    @classmethod
    def new(cls, auth_client: AuthClient) -> tuple[AuthClientCredential, str]:
        """
        Create a new client credential and return (cred, secret).

        The secret is not saved in plaintext, so this is the last time it will be
        available.

        :param auth_client: The client for which a name/secret pair is being generated
        """
        secret = newsecret()
        cred = cls(
            name=make_buid(),
            secret_hash=(
                'blake2b$32$' + blake2b(secret.encode(), digest_size=32).hexdigest()
            ),
            auth_client=auth_client,
        )
        db.session.add(cred)
        return cred, secret


class AuthCode(ScopeMixin, BaseMixin, Model):
    """Short-lived authorization tokens."""

    __tablename__ = 'auth_code'
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False
    )
    account: Mapped[Account] = relationship(Account, foreign_keys=[account_id])
    auth_client_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('auth_client.id'), nullable=False
    )
    auth_client: Mapped[AuthClient] = relationship(back_populates='authcodes')
    login_session_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('login_session.id'), nullable=True
    )
    login_session: Mapped[LoginSession | None] = relationship(LoginSession)
    code: Mapped[str] = sa_orm.mapped_column(
        sa.String(44), default=newsecret, nullable=False
    )
    redirect_uri: Mapped[str] = sa_orm.mapped_column(sa.UnicodeText, nullable=False)
    used: Mapped[bool] = sa_orm.mapped_column(sa.Boolean, default=False, nullable=False)

    def is_valid(self) -> bool:
        """Test if this auth code is still valid."""
        # Time limit: 3 minutes. Should be reasonable enough to load a page
        # on a slow mobile connection, without keeping the code valid too long
        return not self.used and self.created_at >= utcnow() - timedelta(minutes=3)

    @classmethod
    def all_for(cls, account: Account) -> Query[AuthCode]:
        """Return all auth codes for the specified account."""
        return cls.query.filter(cls.account == account)

    @classmethod
    def get_for_client(cls, auth_client: AuthClient, code: str) -> AuthCode | None:
        """Return a matching auth code for the specified auth client."""
        return cls.query.filter(
            cls.auth_client == auth_client, cls.code == code
        ).one_or_none()


class AuthToken(ScopeMixin, BaseMixin, Model):
    """Access tokens for access to data."""

    __tablename__ = 'auth_token'
    # Account id is null for client-only tokens and public clients as the account is
    # identified via login_session.account there
    account_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=True
    )
    account: Mapped[Account | None] = relationship(back_populates='authtokens')
    #: The session in which this token was issued, null for confidential clients
    login_session_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('login_session.id'), nullable=True
    )
    login_session: Mapped[LoginSession | None] = with_roles(
        relationship(LoginSession, back_populates='authtokens'),
        read={'owner'},
    )
    #: The client this auth token is for
    auth_client_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('auth_client.id'), nullable=False, index=True
    )
    auth_client: Mapped[AuthClient] = with_roles(
        relationship(back_populates='authtokens'),
        read={'owner'},
    )
    #: The token
    token: Mapped[str] = sa_orm.mapped_column(
        sa.String(22), default=make_buid, nullable=False, unique=True
    )
    #: The token's type, 'bearer', 'mac' or a URL
    token_type: Mapped[str] = sa_orm.mapped_column(
        sa.String(250), default='bearer', nullable=False
    )
    #: Token secret for 'mac' type
    secret: Mapped[str | None] = sa_orm.mapped_column(sa.String(44), nullable=True)
    #: Secret's algorithm (for 'mac' type)
    algorithm: Mapped[str | None] = sa_orm.mapped_column(sa.String(20), nullable=True)
    #: Token's validity period in seconds, 0 = unlimited
    validity: Mapped[int] = sa_orm.mapped_column(sa.Integer, nullable=False, default=0)
    #: Refresh token, to obtain a new token
    refresh_token: Mapped[str | None] = sa_orm.mapped_column(
        sa.String(22), nullable=True, unique=True
    )

    # Only one auth token per user and client. Add to scope as needed
    __table_args__ = (
        sa.UniqueConstraint('account_id', 'auth_client_id'),
        sa.UniqueConstraint('login_session_id', 'auth_client_id'),
    )

    __roles__ = {
        'owner': {
            'read': {'created_at', 'account'},
            'granted_by': ['account'],
        }
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.token = make_buid()
        if self.effective_user:
            self.refresh_token = make_buid()
        self.secret = newsecret()

    def __repr__(self) -> str:
        """Represent :class:`AuthToken` as a string."""
        return f'<AuthToken {self.token} of {self.auth_client!r} {self.account!r}>'

    @property
    def effective_user(self) -> Account:
        """Return subject user of this auth token."""
        if self.login_session:
            return self.login_session.account
        return cast(Account, self.account)

    @property
    def effective_scope(self) -> list[str]:
        """Return effective scope of this token, combining granted and client scopes."""
        return sorted(set(self.scope) | set(self.auth_client.scope))

    @with_roles(read={'owner'})
    @cached_property
    def last_used(self) -> datetime | None:
        """Return last used timestamp for this auth token."""
        return (
            db.session.query(sa.func.max(auth_client_login_session.c.accessed_at))
            .select_from(auth_client_login_session, LoginSession)
            .filter(
                auth_client_login_session.c.login_session_id == LoginSession.id,
                auth_client_login_session.c.auth_client_id == self.auth_client_id,
                LoginSession.account == self.account,
            )
            .scalar()
        )

    def refresh(self) -> None:
        """Create a new token while retaining the refresh token."""
        if self.refresh_token is not None:
            self.token = make_buid()
            self.secret = newsecret()

    @sa_orm.validates('algorithm')
    def _validate_algorithm(self, _key: str, value: str | None) -> str | None:
        """Set mac token algorithm to one of supported values."""
        if value is None:
            self.secret = None
            return value
        if value not in ['hmac-sha-1', 'hmac-sha-256']:
            raise ValueError(_("Unrecognized algorithm ‘{value}’").format(value=value))
        return value

    def is_valid(self) -> bool:
        """Test if auth token is currently valid."""
        if self.validity == 0:
            return True  # This token is perpetually valid
        now = utcnow()
        if self.created_at < now - timedelta(seconds=self.validity):
            return False
        return True

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        oldtokens = cls.query.filter(cls.account == old_account).all()
        newtokens: dict[int, list[AuthToken]] = {}  # AuthClient: token mapping
        for token in cls.query.filter(cls.account == new_account).all():
            newtokens.setdefault(token.auth_client_id, []).append(token)

        for token in oldtokens:
            merge_performed = False
            if token.auth_client_id in newtokens:
                for newtoken in newtokens[token.auth_client_id]:
                    if newtoken.account == new_account:
                        # There's another token for new_account with the same client.
                        # Just extend the scope there
                        newtoken.scope = set(newtoken.scope) | set(token.scope)
                        db.session.delete(token)
                        merge_performed = True
                        break
            if merge_performed is False:
                token.account = new_account  # Reassign this token to new_account

    @classmethod
    def get(cls, token: str) -> AuthToken | None:
        """
        Return an AuthToken with the matching token.

        :param str token: Token to lookup
        """
        return cls.query.filter(cls.token == token).join(AuthClient).one_or_none()

    @overload
    @classmethod
    def get_for(cls, auth_client: AuthClient, *, account: Account) -> AuthToken | None:
        ...

    @overload
    @classmethod
    def get_for(
        cls, auth_client: AuthClient, *, login_session: LoginSession
    ) -> AuthToken | None:
        ...

    @classmethod
    def get_for(
        cls,
        auth_client: AuthClient,
        *,
        account: Account | None = None,
        login_session: LoginSession | None = None,
    ) -> AuthToken | None:
        """Get an auth token for an auth client and an account or login session."""
        require_one_of(account=account, login_session=login_session)
        if account is not None:
            return cls.query.filter(
                cls.auth_client == auth_client, cls.account == account
            ).one_or_none()
        return cls.query.filter(
            cls.auth_client == auth_client, cls.login_session == login_session
        ).one_or_none()

    @classmethod
    def all(cls, accounts: Query | Sequence[Account]) -> list[AuthToken]:  # noqa: A003
        """Return all AuthToken for the specified accounts."""
        query = cls.query.join(AuthClient)
        if isinstance(accounts, QueryBaseClass):
            count = accounts.count()
            if count == 1:
                return query.filter(AuthToken.account == accounts.first()).all()
            if count > 1:
                return query.filter(
                    AuthToken.account_id.in_(accounts.options(load_only(Account.id)))
                ).all()
        else:
            count = len(accounts)
            if count == 1:
                # Cast users into a list/tuple before accessing [0], as the source
                # may not be an actual list with indexed access. For example,
                # Organization.owner_users is a DynamicAssociationProxy.
                return query.filter(AuthToken.account == tuple(accounts)[0]).all()
            if count > 1:
                return query.filter(
                    AuthToken.account_id.in_([u.id for u in accounts])
                ).all()

        return []

    @classmethod
    def all_for(cls, account: Account) -> Query[AuthToken]:
        """Get all AuthTokens for a specified account (direct only)."""
        return cls.query.filter(cls.account == account)


# This model's name is in plural because it defines multiple permissions within each
# instance
class AuthClientPermissions(BaseMixin, Model):
    """Permissions assigned to an account on a client app."""

    __tablename__ = 'auth_client_permissions'
    __tablename__ = 'auth_client_permissions'
    #: User account that has these permissions
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False
    )
    account: Mapped[Account] = relationship(back_populates='client_permissions')
    #: AuthClient app they are assigned on
    auth_client_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('auth_client.id'), nullable=False, index=True
    )
    auth_client: Mapped[AuthClient] = with_roles(
        relationship(back_populates='account_permissions'),
        grants_via={None: {'owner'}},
    )
    #: The permissions as a string of tokens
    access_permissions: Mapped[str] = sa_orm.mapped_column(
        'permissions', sa.UnicodeText, default='', nullable=False
    )

    # Only one assignment per account and client
    __table_args__ = (sa.UniqueConstraint('account_id', 'auth_client_id'),)

    # Used by auth_client_info.html
    @property
    def pickername(self) -> str:
        """Return label string for identification of the subject account."""
        return self.account.pickername

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        for operm in old_account.client_permissions:
            merge_performed = False
            for nperm in new_account.client_permissions:
                if nperm.auth_client == operm.auth_client:
                    # Merge permission strings
                    tokens = set(operm.access_permissions.split(' '))
                    tokens.update(set(nperm.access_permissions.split(' ')))
                    if ' ' in tokens:
                        tokens.remove(' ')
                    nperm.access_permissions = ' '.join(sorted(tokens))
                    db.session.delete(operm)
                    merge_performed = True
            if not merge_performed:
                operm.account = new_account

    @classmethod
    def get(
        cls, auth_client: AuthClient, account: Account
    ) -> AuthClientPermissions | None:
        """Get permissions for the specified auth client and account."""
        return cls.query.filter(
            cls.auth_client == auth_client, cls.account == account
        ).one_or_none()

    @classmethod
    def all_for(cls, account: Account) -> Query[AuthClientPermissions]:
        """Get all permissions assigned to account for various clients."""
        return cls.query.filter(cls.account == account)

    @classmethod
    def all_forclient(cls, auth_client: AuthClient) -> Query[AuthClientPermissions]:
        """Get all permissions assigned on the specified auth client."""
        return cls.query.filter(cls.auth_client == auth_client)


# This model's name is in plural because it defines multiple permissions within each
# instance
class AuthClientTeamPermissions(BaseMixin, Model):
    """Permissions assigned to a team on a client app."""

    __tablename__ = 'auth_client_team_permissions'
    #: Team which has these permissions
    team_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('team.id'), nullable=False
    )
    team: Mapped[Team] = relationship(back_populates='client_permissions')
    #: AuthClient app they are assigned on
    auth_client_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('auth_client.id'), nullable=False, index=True
    )
    auth_client: Mapped[AuthClient] = with_roles(
        relationship(
            back_populates='team_permissions',
        ),
        grants_via={None: {'owner'}},
    )
    #: The permissions as a string of tokens
    access_permissions: Mapped[str] = sa_orm.mapped_column(
        'permissions', sa.UnicodeText, default='', nullable=False
    )

    # Only one assignment per team and client
    __table_args__ = (sa.UniqueConstraint('team_id', 'auth_client_id'),)

    # Used by auth_client_info.html
    @property
    def pickername(self) -> str:
        """Return label string for identification of the subject team."""
        return self.team.pickername

    @classmethod
    def get(
        cls, auth_client: AuthClient, team: Team
    ) -> AuthClientTeamPermissions | None:
        """Get permissions for the specified auth client and team."""
        return cls.query.filter(
            cls.auth_client == auth_client, cls.team == team
        ).one_or_none()

    @classmethod
    def all_for(
        cls, auth_client: AuthClient, account: Account
    ) -> Query[AuthClientTeamPermissions]:
        """Get all permissions for the specified account via their teams."""
        return cls.query.filter(
            cls.auth_client == auth_client,
            cls.team_id.in_([team.id for team in account.member_teams]),
        )

    @classmethod
    def all_forclient(cls, auth_client: AuthClient) -> Query[AuthClientTeamPermissions]:
        """Get all permissions assigned on the specified auth client."""
        return cls.query.filter(cls.auth_client == auth_client)


@reopen(Account)
class __Account:
    def revoke_all_auth_tokens(self) -> None:
        """Revoke all auth tokens directly linked to the account."""
        AuthToken.all_for(cast(Account, self)).delete(synchronize_session=False)

    def revoke_all_auth_client_permissions(self) -> None:
        """Revoke all permissions on client apps assigned to account."""
        AuthClientPermissions.all_for(cast(Account, self)).delete(
            synchronize_session=False
        )
