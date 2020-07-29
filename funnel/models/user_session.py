from datetime import timedelta

from coaster.utils import buid as make_buid
from coaster.utils import utcnow

from ..signals import session_revoked
from . import BaseMixin, UuidMixin, db
from .user import User

__all__ = ['UserSession', 'auth_client_user_session']


#: When a user logs into an client app, the user's session is logged against
#: the client app in this table
auth_client_user_session = db.Table(
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

    ipaddr = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.UnicodeText, nullable=False)
    #: The login service that was used to make this session
    login_service = db.Column(db.Unicode, nullable=True)

    accessed_at = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    revoked_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    sudo_enabled_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )

    def __init__(self, **kwargs):
        super(UserSession, self).__init__(**kwargs)
        if not self.buid:
            self.buid = make_buid()

    def __repr__(self):
        return f'<UserSession {self.buid}>'

    @property
    def has_sudo(self):
        return self.sudo_enabled_at > utcnow() - timedelta(hours=1)

    def set_sudo(self):
        self.sudo_enabled_at = db.func.utcnow()

    def revoke(self):
        if not self.revoked_at:
            self.revoked_at = db.func.utcnow()
            session_revoked.send(self)

    @classmethod
    def get(cls, buid):
        return cls.query.filter_by(buid=buid).one_or_none()

    @classmethod
    def authenticate(cls, buid):
        return cls.query.filter(
            # Session key must match.
            cls.buid == buid,
            # Sessions are valid for one year...
            cls.accessed_at > db.func.utcnow() - timedelta(days=365),
            # ...unless explicitly revoked (or user logged out)
            cls.revoked_at.is_(None),
        ).one_or_none()


User.active_sessions = db.relationship(
    UserSession,
    lazy='dynamic',
    primaryjoin=db.and_(
        UserSession.user_id == User.id,
        UserSession.accessed_at > db.func.utcnow() - timedelta(days=365),  # See ^
        UserSession.revoked_at.is_(None),
    ),
    order_by=UserSession.accessed_at.desc(),
)
