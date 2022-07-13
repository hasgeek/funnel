"""Model for a user's auth (login) session."""

from __future__ import annotations

from datetime import timedelta

from coaster.utils import utcnow

from ..signals import session_revoked
from . import BaseMixin, UuidMixin, db
from .helpers import reopen
from .user import User

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
auth_client_user_session: db.Table = db.Table(
    'auth_client_user_session',
    db.Model.metadata,
    db.Column(
        'auth_client_id',
        None,
        db.ForeignKey('auth_client.id'),
        nullable=False,
        primary_key=True,
    ),
    db.Column(
        'user_session_id',
        None,
        db.ForeignKey('user_session.id'),
        nullable=False,
        primary_key=True,
    ),
    db.Column(
        'created_at',
        db.TIMESTAMP(timezone=True),
        nullable=False,
        default=db.func.utcnow(),
    ),
    db.Column(
        'accessed_at',
        db.TIMESTAMP(timezone=True),
        nullable=False,
        default=db.func.utcnow(),
    ),
)


class UserSession(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'user_session'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        User, backref=db.backref('all_user_sessions', cascade='all', lazy='dynamic')
    )

    #: User's last known IP address
    ipaddr = db.Column(db.String(45), nullable=False)
    #: City geonameid from IP address
    geonameid_city = db.Column(db.Integer, nullable=True)
    #: State/subdivision geonameid from IP address
    geonameid_subdivision = db.Column(db.Integer, nullable=True)
    #: Country geonameid from IP address
    geonameid_country = db.Column(db.Integer, nullable=True)
    #: User's network, from IP address
    geoip_asn = db.Column(db.Integer, nullable=True)
    #: User agent
    user_agent = db.Column(db.UnicodeText, nullable=False)
    #: The login service that was used to make this session
    login_service = db.Column(db.Unicode, nullable=True)

    accessed_at = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    revoked_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    sudo_enabled_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
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
        self.sudo_enabled_at = db.func.utcnow()

    def revoke(self):
        if not self.revoked_at:
            self.revoked_at = db.func.utcnow()
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
                    cls.accessed_at > db.func.utcnow() - USER_SESSION_VALIDITY_PERIOD,
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


@reopen(User)
class __User:
    active_user_sessions = db.relationship(
        UserSession,
        lazy='dynamic',
        primaryjoin=db.and_(
            UserSession.user_id == User.id,
            UserSession.accessed_at > db.func.utcnow() - USER_SESSION_VALIDITY_PERIOD,
            UserSession.revoked_at.is_(None),
        ),
        order_by=UserSession.accessed_at.desc(),
        viewonly=True,
    )
