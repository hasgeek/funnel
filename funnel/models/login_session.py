"""Model for a user's auth (login) session."""

from __future__ import annotations

from datetime import timedelta

from coaster.utils import utcnow

from ..signals import session_revoked
from . import (
    BaseMixin,
    DynamicMapped,
    Mapped,
    Model,
    UuidMixin,
    backref,
    relationship,
    sa,
)
from .account import Account
from .helpers import reopen

__all__ = [
    'LoginSession',
    'LoginSessionError',
    'LoginSessionExpiredError',
    'LoginSessionRevokedError',
    'LoginSessionInactiveUserError',
    'auth_client_login_session',
    'LOGIN_SESSION_VALIDITY_PERIOD',
]


class LoginSessionError(Exception):
    """Base exception for user session errors."""


class LoginSessionExpiredError(LoginSessionError):
    """This user session has expired and cannot be marked as currently active."""


class LoginSessionRevokedError(LoginSessionError):
    """This user session has been revoked and cannot be marked as currently active."""


class LoginSessionInactiveUserError(LoginSessionError):
    """This user is not in ACTIVE state and cannot have a currently active session."""


LOGIN_SESSION_VALIDITY_PERIOD = timedelta(days=365)

#: When a user logs into an client app, the user's session is logged against
#: the client app in this table
auth_client_login_session = sa.Table(
    'auth_client_login_session',
    Model.metadata,
    sa.Column(
        'auth_client_id',
        sa.Integer,
        sa.ForeignKey('auth_client.id'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'login_session_id',
        sa.Integer,
        sa.ForeignKey('login_session.id'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'created_at',
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        default=sa.func.utcnow(),
    ),
    sa.Column(
        'accessed_at',
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        default=sa.func.utcnow(),
    ),
)


class LoginSession(UuidMixin, BaseMixin, Model):
    __tablename__ = 'login_session'

    account_id: Mapped[int] = sa.orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False
    )
    account: Mapped[Account] = relationship(
        Account,
        backref=backref('all_login_sessions', cascade='all', lazy='dynamic'),
    )

    #: User's last known IP address
    ipaddr = sa.orm.mapped_column(sa.String(45), nullable=False)
    #: City geonameid from IP address
    geonameid_city = sa.orm.mapped_column(sa.Integer, nullable=True)
    #: State/subdivision geonameid from IP address
    geonameid_subdivision = sa.orm.mapped_column(sa.Integer, nullable=True)
    #: Country geonameid from IP address
    geonameid_country = sa.orm.mapped_column(sa.Integer, nullable=True)
    #: User's network, from IP address
    geoip_asn = sa.orm.mapped_column(sa.Integer, nullable=True)
    #: User agent
    user_agent = sa.orm.mapped_column(sa.UnicodeText, nullable=False)
    #: The login service that was used to make this session
    login_service = sa.orm.mapped_column(sa.Unicode, nullable=True)

    accessed_at = sa.orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=False)
    revoked_at = sa.orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    sudo_enabled_at = sa.orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )

    def __repr__(self) -> str:
        """Represent :class:`UserSession` as a string."""
        return f'<UserSession {self.buid}>'

    @property
    def has_sudo(self) -> bool:
        return (
            self.sudo_enabled_at is None  # New session, not yet written to db
            or self.sudo_enabled_at > utcnow() - timedelta(minutes=15)
        )

    def set_sudo(self) -> None:
        self.sudo_enabled_at = sa.func.utcnow()

    def revoke(self) -> None:
        if not self.revoked_at:
            self.revoked_at = sa.func.utcnow()
            self.authtokens.delete(synchronize_session='fetch')
            session_revoked.send(self)

    @classmethod
    def get(cls, buid: str) -> LoginSession | None:
        return cls.query.filter_by(buid=buid).one_or_none()

    @classmethod
    def authenticate(cls, buid: str, silent: bool = False) -> LoginSession | None:
        """
        Retrieve a user session that is supposed to be active.

        If a session is invalid, exceptions will be raised to indicate the problem,
        unless silent mode is enabled.
        """
        if silent:
            return (
                cls.query.join(Account)
                .filter(
                    # Session key must match.
                    cls.buid == buid,
                    # Sessions are valid for one year...
                    cls.accessed_at > sa.func.utcnow() - LOGIN_SESSION_VALIDITY_PERIOD,
                    # ...unless explicitly revoked (or user logged out).
                    cls.revoked_at.is_(None),
                    # Account must be active
                    Account.state.ACTIVE,
                )
                .one_or_none()
            )

        # Not silent? Raise exceptions on expired and revoked sessions
        login_session = cls.query.join(Account).filter(cls.buid == buid).one_or_none()
        if login_session is not None:
            if login_session.accessed_at <= utcnow() - LOGIN_SESSION_VALIDITY_PERIOD:
                raise LoginSessionExpiredError(login_session)
            if login_session.revoked_at is not None:
                raise LoginSessionRevokedError(login_session)
            if not login_session.account.state.ACTIVE:
                raise LoginSessionInactiveUserError(login_session)
        return login_session


@reopen(Account)
class __Account:
    active_login_sessions: DynamicMapped[LoginSession] = relationship(
        LoginSession,
        lazy='dynamic',
        primaryjoin=sa.and_(
            LoginSession.account_id == Account.id,
            LoginSession.accessed_at > sa.func.utcnow() - LOGIN_SESSION_VALIDITY_PERIOD,
            LoginSession.revoked_at.is_(None),
        ),
        order_by=LoginSession.accessed_at.desc(),
        viewonly=True,
    )
