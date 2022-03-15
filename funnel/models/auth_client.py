from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import blake2b, sha256
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union, overload
import urllib.parse

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import load_only
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.query import Query as QueryBaseClass

from werkzeug.utils import cached_property

from baseframe import _
from coaster.sqlalchemy import with_roles
from coaster.utils import buid as make_buid
from coaster.utils import newsecret, require_one_of, utcnow

from ..typing import OptionalMigratedTables
from . import BaseMixin, UuidMixin, db
from .user import Organization, Team, User
from .user_session import UserSession, auth_client_user_session

__all__ = [
    'AuthCode',
    'AuthToken',
    'AuthClient',
    'AuthClientCredential',
    'AuthClientTeamPermissions',
    'AuthClientUserPermissions',
]


class ScopeMixin:
    __scope_null_allowed__ = False

    _scope: str

    @declared_attr  # type: ignore[no-redef]
    def _scope(cls):
        return db.Column('scope', db.UnicodeText, nullable=cls.__scope_null_allowed__)

    scope: Iterable[str]

    @declared_attr  # type: ignore[no-redef]
    def scope(cls):
        @property
        def scope(self) -> Tuple[str, ...]:
            if not self._scope:
                return ()
            return tuple(sorted(self._scope.split()))

        @scope.setter
        def scope(self, value: Optional[Union[str, Iterable]]) -> None:
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

        return db.synonym('_scope', descriptor=scope)

    def add_scope(self, additional: Union[str, Iterable]) -> None:
        if isinstance(additional, str):
            additional = [additional]
        self.scope = set(self.scope).union(set(additional))


class AuthClient(ScopeMixin, UuidMixin, BaseMixin, db.Model):
    """OAuth client application."""

    __tablename__ = 'auth_client'
    __scope_null_allowed__ = True
    #: User who owns this client
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    user = with_roles(
        db.relationship(
            User,
            primaryjoin=user_id == User.id,
            backref=db.backref('clients', cascade='all'),
        ),
        read={'all'},
        write={'owner'},
        grants={'owner'},
    )
    #: Organization that owns this client. Only one of this or user must be set
    organization_id = db.Column(None, db.ForeignKey('organization.id'), nullable=True)
    organization = with_roles(
        db.relationship(
            Organization,
            primaryjoin=organization_id == Organization.id,
            backref=db.backref('clients', cascade='all'),
        ),
        read={'all'},
        write={'owner'},
        grants_via={None: {'owner': 'owner', 'admin': 'owner'}},
    )
    #: Human-readable title
    title = with_roles(
        db.Column(db.Unicode(250), nullable=False), read={'all'}, write={'owner'}
    )
    #: Long description
    description = with_roles(
        db.Column(db.UnicodeText, nullable=False, default=''),
        read={'all'},
        write={'owner'},
    )
    #: Confidential or public client? Public has no secret key
    confidential = with_roles(
        db.Column(db.Boolean, nullable=False), read={'all'}, write={'owner'}
    )
    #: Website
    website = with_roles(
        db.Column(db.UnicodeText, nullable=False), read={'all'}, write={'owner'}
    )
    #: Redirect URIs (one or more)
    _redirect_uris = db.Column(
        'redirect_uri', db.UnicodeText, nullable=True, default=''
    )
    #: Back-end notification URI (TODO: deprecated, needs better architecture)
    notification_uri = with_roles(
        db.Column(db.UnicodeText, nullable=True, default=''), rw={'owner'}
    )
    #: Active flag
    active = db.Column(db.Boolean, nullable=False, default=True)
    #: Allow anyone to login to this app?
    allow_any_login = with_roles(
        db.Column(db.Boolean, nullable=False, default=True),
        read={'all'},
        write={'owner'},
    )
    #: Trusted flag: trusted clients are authorized to access user data
    #: without user consent, but the user must still login and identify themself.
    #: When a single provider provides multiple services, each can be declared
    #: as a trusted client to provide single sign-in across the services.
    #: However, resources in the scope column (via ScopeMixin) are granted for
    #: any arbitrary user without explicit user authorization.
    trusted = with_roles(
        db.Column(db.Boolean, nullable=False, default=False), read={'all'}
    )

    user_sessions = db.relationship(
        UserSession,
        lazy='dynamic',
        secondary=auth_client_user_session,
        backref=db.backref('auth_clients', lazy='dynamic'),
    )

    __table_args__ = (
        db.CheckConstraint(
            db.case([(user_id.isnot(None), 1)], else_=0)
            + db.case([(organization_id.isnot(None), 1)], else_=0)
            == 1,
            name='auth_client_owner_check',
        ),
    )

    __roles__ = {
        'all': {
            'read': {'urls'},
            'call': {'url_for'},
        }
    }

    def __repr__(self):
        """Represent :class:`AuthClient` as a string."""
        return f'<AuthClient "{self.title}" {self.buid}>'

    def secret_is(self, candidate: str, name: str) -> bool:
        """Check if the provided client secret is valid."""
        credential = self.credentials[name]
        return credential.secret_is(candidate)

    @property
    def redirect_uris(self) -> Tuple:
        return tuple(self._redirect_uris.split())

    @redirect_uris.setter
    def redirect_uris(self, value: Iterable) -> None:
        self._redirect_uris = '\r\n'.join(value)

    with_roles(redirect_uris, rw={'owner'})

    @property
    def redirect_uri(self):
        uris = self.redirect_uris  # Assign to local var to avoid splitting twice
        if uris:
            return uris[0]

    def host_matches(self, url: str) -> bool:
        netloc = urllib.parse.urlsplit(url or '').netloc
        if netloc:
            return netloc in (
                urllib.parse.urlsplit(r).netloc
                for r in (self.redirect_uris + (self.website,))
            )
        return False

    @property
    def owner(self):
        return self.user or self.organization

    with_roles(owner, read={'all'})

    def owner_is(self, user: User) -> bool:
        # Legacy method for ownership test
        return 'owner' in self.roles_for(user)

    def authtoken_for(
        self, user: Optional[User], user_session: Optional[UserSession] = None
    ) -> Optional[AuthToken]:
        """
        Return the authtoken for this user and client.

        Only works for confidential clients.
        """
        if self.confidential:
            if user is None:
                raise ValueError("User not provided")
            return AuthToken.get_for(auth_client=self, user=user)
        elif user_session and user_session.user == user:
            return AuthToken.get_for(auth_client=self, user_session=user_session)
        return None

    def allow_login_for(self, actor: User) -> bool:
        if self.allow_any_login:
            return True
        if self.user:
            if AuthClientUserPermissions.get(self, actor):
                return True
        else:
            if AuthClientTeamPermissions.all_for(self, actor).first():
                return True
        return False

    @classmethod
    def get(cls, buid: str) -> Optional[AuthClient]:
        """
        Return a AuthClient identified by its client buid or namespace.

        Only returns active clients.

        :param str buid: AuthClient buid to lookup
        """
        return cls.query.filter_by(buid=buid, active=True).one_or_none()

    @classmethod
    def all_for(cls, user: Optional[User]):
        if user is None:
            return cls.query.order_by(cls.title)
        else:
            return cls.query.filter(
                db.or_(
                    cls.user == user,
                    cls.organization_id.in_(user.organizations_as_owner_ids()),
                )
            ).order_by(cls.title)


class AuthClientCredential(BaseMixin, db.Model):
    """
    AuthClient key and secret hash.

    This uses unsalted Blake2 (64-bit) instead of a salted hash or a more secure hash
    like bcrypt because:

    1. Secrets are UUID-based and unique before hashing. Salting is only beneficial when
       the source values may be reused.
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
    auth_client_id = db.Column(None, db.ForeignKey('auth_client.id'), nullable=False)
    auth_client: AuthClient = with_roles(
        db.relationship(
            AuthClient,
            primaryjoin=auth_client_id == AuthClient.id,
            backref=db.backref(
                'credentials',
                cascade='all',
                collection_class=attribute_mapped_collection('name'),
            ),
        ),
        grants_via={None: {'owner'}},
    )

    #: OAuth client key
    name = db.Column(db.String(22), nullable=False, unique=True, default=make_buid)
    #: User description for this credential
    title = db.Column(db.Unicode(250), nullable=False, default='')
    #: OAuth client secret, hashed
    secret_hash = db.Column(db.Unicode, nullable=False)
    #: When was this credential last used for an API call?
    accessed_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    def secret_is(self, candidate: str, upgrade_hash: bool = False):
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
    def get(cls, name: str):
        return cls.query.filter_by(name=name).one_or_none()

    @classmethod
    def new(cls, auth_client: AuthClient):
        """
        Create a new client credential and return (cred, secret).

        The secret is not saved in plaintext, so this is the last time it will be
        available.

        :param auth_client: The client for which a name/secret pair is being generated
        """
        cred = cls(auth_client=auth_client, name=make_buid())
        secret = newsecret()
        cred.secret_hash = (
            'blake2b$32$' + blake2b(secret.encode(), digest_size=32).hexdigest()
        )
        return cred, secret


class AuthCode(ScopeMixin, BaseMixin, db.Model):
    """Short-lived authorization tokens."""

    __tablename__ = 'auth_code'
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user: User = db.relationship(User, primaryjoin=user_id == User.id)
    auth_client_id = db.Column(None, db.ForeignKey('auth_client.id'), nullable=False)
    auth_client: AuthClient = db.relationship(
        AuthClient,
        primaryjoin=auth_client_id == AuthClient.id,
        backref=db.backref('authcodes', cascade='all'),
    )
    user_session_id = db.Column(None, db.ForeignKey('user_session.id'), nullable=True)
    user_session: UserSession = db.relationship(UserSession)
    code = db.Column(db.String(44), default=newsecret, nullable=False)
    redirect_uri = db.Column(db.UnicodeText, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    def is_valid(self) -> bool:
        # Time limit: 3 minutes. Should be reasonable enough to load a page
        # on a slow mobile connection, without keeping the code valid too long
        return not self.used and self.created_at >= utcnow() - timedelta(minutes=3)

    @classmethod
    def all_for(cls, user: User):
        return cls.query.filter_by(user=user)

    @classmethod
    def get_for_client(cls, auth_client: AuthClient, code: str):
        return cls.query.filter_by(auth_client=auth_client, code=code).one_or_none()


class AuthToken(ScopeMixin, BaseMixin, db.Model):
    """Access tokens for access to data."""

    __tablename__ = 'auth_token'
    # Null for client-only tokens and public clients (user is identified via user_session.user there)
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    _user: User = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('authtokens', lazy='dynamic', cascade='all'),
    )
    #: The session in which this token was issued, null for confidential clients
    user_session_id = db.Column(None, db.ForeignKey('user_session.id'), nullable=True)
    user_session: UserSession = with_roles(
        db.relationship(UserSession, backref=db.backref('authtokens', lazy='dynamic')),
        read={'owner'},
    )
    #: The client this authtoken is for
    auth_client_id = db.Column(
        None, db.ForeignKey('auth_client.id'), nullable=False, index=True
    )
    auth_client: AuthClient = with_roles(
        db.relationship(
            AuthClient,
            primaryjoin=auth_client_id == AuthClient.id,
            backref=db.backref('authtokens', lazy='dynamic', cascade='all'),
        ),
        read={'owner'},
    )
    #: The token
    token = db.Column(db.String(22), default=make_buid, nullable=False, unique=True)
    #: The token's type
    token_type = db.Column(
        db.String(250), default='bearer', nullable=False
    )  # 'bearer', 'mac' or a URL
    #: Token secret for 'mac' type
    secret = db.Column(db.String(44), nullable=True)
    #: Secret's algorithm (for 'mac' type)
    _algorithm = db.Column('algorithm', db.String(20), nullable=True)
    #: Token's validity, 0 = unlimited
    validity = db.Column(
        db.Integer, nullable=False, default=0
    )  # Validity period in seconds
    #: Refresh token, to obtain a new token
    refresh_token = db.Column(db.String(22), nullable=True, unique=True)

    # Only one authtoken per user and client. Add to scope as needed
    __table_args__ = (
        db.UniqueConstraint('user_id', 'auth_client_id'),
        db.UniqueConstraint('user_session_id', 'auth_client_id'),
    )

    __roles__ = {
        'owner': {
            'read': {'created_at', 'user'},
            'granted_by': {'user'},
        }
    }

    @property
    def user(self) -> User:
        if self.user_session:
            return self.user_session.user
        else:
            return self._user

    @user.setter
    def user(self, value: User):
        self._user = value

    user = db.synonym('_user', descriptor=user)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.token = make_buid()
        if self._user:
            self.refresh_token = make_buid()
        self.secret = newsecret()

    def __repr__(self):
        """Represent :class:`AuthToken` as a string."""
        return '<AuthToken {token} of {auth_client} {user}>'.format(
            token=self.token,
            auth_client=repr(self.auth_client)[1:-1],
            user=repr(self.user)[1:-1],
        )

    @property
    def effective_scope(self) -> List:
        return sorted(set(self.scope) | set(self.auth_client.scope))

    @with_roles(read={'owner'})
    @cached_property
    def last_used(self) -> datetime:
        return (
            db.session.query(db.func.max(auth_client_user_session.c.accessed_at))
            .select_from(auth_client_user_session, UserSession)
            .filter(
                auth_client_user_session.c.user_session_id == UserSession.id,
                auth_client_user_session.c.auth_client_id == self.auth_client_id,
                UserSession.user == self.user,
            )
            .scalar()
        )

    def refresh(self) -> None:
        """Create a new token while retaining the refresh token."""
        if self.refresh_token is not None:
            self.token = make_buid()
            self.secret = newsecret()

    @property
    def algorithm(self):
        return self._algorithm

    @algorithm.setter
    def algorithm(self, value: Optional[str]):
        if value is None:
            self._algorithm = None
            self.secret = None
        elif value in ['hmac-sha-1', 'hmac-sha-256']:
            self._algorithm = value
        else:
            raise ValueError(_("Unrecognized algorithm ‘{value}’").format(value=value))

    algorithm = db.synonym('_algorithm', descriptor=algorithm)

    def is_valid(self) -> bool:
        if self.validity == 0:
            return True  # This token is perpetually valid
        now = utcnow()
        if self.created_at < now - timedelta(seconds=self.validity):
            return False
        return True

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
        if not old_user or not new_user:
            return None  # Don't mess with client-only tokens
        oldtokens = cls.query.filter_by(user=old_user).all()
        newtokens: Dict[int, List[AuthToken]] = {}  # AuthClient: token mapping
        for token in cls.query.filter_by(user=new_user).all():
            newtokens.setdefault(token.auth_client_id, []).append(token)

        for token in oldtokens:
            merge_performed = False
            if token.auth_client_id in newtokens:
                for newtoken in newtokens[token.auth_client_id]:
                    if newtoken.user == new_user:
                        # There's another token for newuser with the same client.
                        # Just extend the scope there
                        newtoken.scope = set(newtoken.scope) | set(token.scope)
                        db.session.delete(token)
                        merge_performed = True
                        break
            if merge_performed is False:
                token.user = new_user  # Reassign this token to newuser
        return None

    @classmethod
    def get(cls, token: str) -> Optional[AuthToken]:
        """
        Return an AuthToken with the matching token.

        :param str token: Token to lookup
        """
        query = cls.query.filter_by(token=token).options(
            db.joinedload(cls.auth_client).load_only('id', '_scope')
        )
        return query.one_or_none()

    @overload
    @classmethod
    def get_for(cls, auth_client: AuthClient, *, user: User) -> Optional[AuthToken]:
        ...

    @overload
    @classmethod
    def get_for(
        cls, auth_client: AuthClient, *, user_session: UserSession
    ) -> Optional[AuthToken]:
        ...

    @classmethod
    def get_for(
        cls,
        auth_client: AuthClient,
        *,
        user: Optional[User] = None,
        user_session: Optional[UserSession] = None,
    ) -> Optional[AuthToken]:
        require_one_of(user=user, user_session=user_session)
        if user is not None:
            return cls.query.filter_by(auth_client=auth_client, user=user).one_or_none()
        else:
            return cls.query.filter_by(
                auth_client=auth_client, user_session=user_session
            ).one_or_none()

    @classmethod
    def all(cls, users: Union[QueryBaseClass, Sequence[User]]) -> List[AuthToken]:
        """Return all AuthToken for the specified users."""
        query = cls.query.options(
            db.joinedload(cls.auth_client).load_only('id', '_scope')
        )
        if isinstance(users, QueryBaseClass):
            count = users.count()
            if count == 1:
                return query.filter_by(user=users.first()).all()
            elif count > 1:
                return query.filter(
                    AuthToken.user_id.in_(users.options(load_only('id')))
                ).all()
        else:
            count = len(users)
            if count == 1:
                # Cast users into a list/tuple before accessing [0], as the source
                # may not be an actual list with indexed access. For example,
                # Organization.owner_users is a DynamicAssociationProxy.
                return query.filter_by(user=tuple(users)[0]).all()
            elif count > 1:
                return query.filter(AuthToken.user_id.in_([u.id for u in users])).all()

        return []


# This model's name is in plural because it defines multiple permissions within each
# instance
class AuthClientUserPermissions(BaseMixin, db.Model):
    __tablename__ = 'auth_client_user_permissions'
    #: User who has these permissions
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user: User = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('client_permissions', cascade='all'),
    )
    #: AuthClient app they are assigned on
    auth_client_id = db.Column(
        None, db.ForeignKey('auth_client.id'), nullable=False, index=True
    )
    auth_client: AuthClient = with_roles(
        db.relationship(
            AuthClient,
            primaryjoin=auth_client_id == AuthClient.id,
            backref=db.backref('user_permissions', cascade='all'),
        ),
        grants_via={None: {'owner'}},
    )
    #: The permissions as a string of tokens
    access_permissions = db.Column(
        'permissions', db.UnicodeText, default='', nullable=False
    )

    # Only one assignment per user and client
    __table_args__ = (db.UniqueConstraint('user_id', 'auth_client_id'),)

    # Used by auth_client_info.html
    @property
    def pickername(self) -> str:
        return self.user.pickername

    # Used by auth_client_info.html for url_for
    @property
    def buid(self) -> str:
        return self.user.buid

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
        for operm in old_user.client_permissions:
            merge_performed = False
            for nperm in new_user.client_permissions:
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
                operm.user = new_user
        return None

    @classmethod
    def get(cls, auth_client: AuthClient, user: User) -> AuthClientUserPermissions:
        return cls.query.filter_by(auth_client=auth_client, user=user).one_or_none()

    @classmethod
    def all_forclient(cls, auth_client: AuthClient) -> QueryBaseClass:
        return cls.query.filter_by(auth_client=auth_client)


# This model's name is in plural because it defines multiple permissions within each
# instance
class AuthClientTeamPermissions(BaseMixin, db.Model):
    __tablename__ = 'auth_client_team_permissions'
    #: Team which has these permissions
    team_id = db.Column(None, db.ForeignKey('team.id'), nullable=False)
    team: Team = db.relationship(
        Team,
        primaryjoin=team_id == Team.id,
        backref=db.backref('client_permissions', cascade='all'),
    )
    #: AuthClient app they are assigned on
    auth_client_id = db.Column(
        None, db.ForeignKey('auth_client.id'), nullable=False, index=True
    )
    auth_client: AuthClient = with_roles(
        db.relationship(
            AuthClient,
            primaryjoin=auth_client_id == AuthClient.id,
            backref=db.backref('team_permissions', cascade='all'),
        ),
        grants_via={None: {'owner'}},
    )
    #: The permissions as a string of tokens
    access_permissions = db.Column(
        'permissions', db.UnicodeText, default='', nullable=False
    )

    # Only one assignment per team and client
    __table_args__ = (db.UniqueConstraint('team_id', 'auth_client_id'),)

    # Used by auth_client_info.html
    @property
    def pickername(self) -> str:
        return self.team.pickername

    # Used by auth_client_info.html for url_for
    @property
    def buid(self) -> str:
        return self.team.buid

    @classmethod
    def get(cls, auth_client: AuthClient, team: Team) -> AuthClientTeamPermissions:
        return cls.query.filter_by(auth_client=auth_client, team=team).one_or_none()

    @classmethod
    def all_for(cls, auth_client: AuthClient, user: User) -> QueryBaseClass:
        return cls.query.filter_by(auth_client=auth_client).filter(
            cls.team_id.in_([team.id for team in user.teams])
        )

    @classmethod
    def all_forclient(cls, auth_client: AuthClient) -> QueryBaseClass:
        return cls.query.filter_by(auth_client=auth_client)
