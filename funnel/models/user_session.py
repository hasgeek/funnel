"""Model for a user's auth (login) session."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import

from coaster.utils import utcnow

from ..signals import session_revoked
from . import BaseMixin, Mapped, UuidMixin, db, sa
from .account import Account, User
from .helpers import reopen

__all__ = [
    'UserSession',
    'UserSessionError',
    'UserSessionExpiredError',
    'UserSessionRevokedError',
    'UserSessionInactiveUserError',
    'auth_client_user_session',
    'USER_SESSION_VALIDITY_PERIOD',
]


class UserSessionError(Exception):
    """Base exception for user session errors."""


class UserSessionExpiredError(UserSessionError):
    """This user session has expired and cannot be marked as currently active."""


class UserSessionRevokedError(UserSessionError):
    """This user session has been revoked and cannot be marked as currently active."""


class UserSessionInactiveUserError(UserSessionError):
    """This user is not in ACTIVE state and cannot have a currently active session."""


USER_SESSION_VALIDITY_PERIOD = timedelta(days=365)

#: When a user logs into an client app, the user's session is logged against
#: the client app in this table
auth_client_user_session: sa.Table = sa.Table(
    'auth_client_user_session',
    db.Model.metadata,  # type: ignore[has-type]
    sa.Column(
        'auth_client_id',
        sa.Integer,
        sa.ForeignKey('auth_client.id'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'user_session_id',
        sa.Integer,
        sa.ForeignKey('user_session.id'),
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


class UserSession(UuidMixin, BaseMixin, db.Model):  # type: ignore[name-defined]
    __tablename__ = 'user_session'
    __allow_unmapped__ = True

    user_id = sa.Column(sa.Integer, sa.ForeignKey('account.id'), nullable=False)
    user: Mapped[User] = sa.orm.relationship(
        User, backref=sa.orm.backref('all_user_sessions', cascade='all', lazy='dynamic')
    )

    #: User's last known IP address
    ipaddr = sa.Column(sa.String(45), nullable=False)
    #: City geonameid from IP address
    geonameid_city = sa.Column(sa.Integer, nullable=True)
    #: State/subdivision geonameid from IP address
    geonameid_subdivision = sa.Column(sa.Integer, nullable=True)
    #: Country geonameid from IP address
    geonameid_country = sa.Column(sa.Integer, nullable=True)
    #: User's network, from IP address
    geoip_asn = sa.Column(sa.Integer, nullable=True)
    #: User agent
    user_agent = sa.Column(sa.UnicodeText, nullable=False)
    #: The login service that was used to make this session
    login_service = sa.Column(sa.Unicode, nullable=True)

    accessed_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False)
    revoked_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)
    sudo_enabled_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )

    def __repr__(self) -> str:
        """Represent :class:`UserSession` as a string."""
        return f'<UserSession {self.buid}>'

    @property
    def has_sudo(self):
        return (
            self.sudo_enabled_at is None  # New session, not yet written to db
            or self.sudo_enabled_at > utcnow() - timedelta(minutes=15)
        )

    def set_sudo(self):
        self.sudo_enabled_at = sa.func.utcnow()

    def revoke(self):
        if not self.revoked_at:
            self.revoked_at = sa.func.utcnow()
            self.authtokens.delete(synchronize_session='fetch')
            session_revoked.send(self)

    @classmethod
    def get(cls, buid):
        return cls.query.filter_by(buid=buid).one_or_none()

    @classmethod
    def authenticate(cls, buid, silent=False):
        """
        Retrieve a user session that is supposed to be active.

        If a session is invalid, exceptions will be raised to indicate the problem,
        unless silent mode is enabled.
        """
        if silent:
            return (
                cls.query.join(User)
                .filter(
                    # Session key must match.
                    cls.buid == buid,
                    # Sessions are valid for one year...
                    cls.accessed_at > sa.func.utcnow() - USER_SESSION_VALIDITY_PERIOD,
                    # ...unless explicitly revoked (or user logged out).
                    cls.revoked_at.is_(None),
                    # User account must be active
                    User.state.ACTIVE,
                )
                .one_or_none()
            )

        # Not silent? Raise exceptions on expired and revoked sessions
        user_session = cls.query.join(User).filter(cls.buid == buid).one_or_none()
        if user_session is not None:
            if user_session.accessed_at <= utcnow() - USER_SESSION_VALIDITY_PERIOD:
                raise UserSessionExpiredError(user_session)
            if user_session.revoked_at is not None:
                raise UserSessionRevokedError(user_session)
            if not user_session.user.state.ACTIVE:
                raise UserSessionInactiveUserError(user_session)
        return user_session


@reopen(Account)
class __Account:
    active_user_sessions = sa.orm.relationship(
        UserSession,
        lazy='dynamic',
        primaryjoin=sa.and_(
            UserSession.user_id == User.id,
            UserSession.accessed_at > sa.func.utcnow() - USER_SESSION_VALIDITY_PERIOD,
            UserSession.revoked_at.is_(None),
        ),
        order_by=UserSession.accessed_at.desc(),
        viewonly=True,
    )
