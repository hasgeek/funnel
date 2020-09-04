from baseframe import __
from coaster.sqlalchemy import with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, Comment, SiteMembership, User, UuidMixin, db

__all__ = ['MODERATOR_REPORT_TYPE', 'CommentModeratorReport']


class MODERATOR_REPORT_TYPE(LabeledEnum):  # NOQA: N801
    OK = (0, 'ok', __("Not spam"))
    SPAM = (1, 'spam', __("Spam"))


class CommentModeratorReport(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'comment_moderator_report'
    __uuid_primary_key__ = True

    comment_id = db.Column(
        None, db.ForeignKey('comment.id'), nullable=False, index=True
    )
    comment = db.relationship(
        Comment,
        primaryjoin=comment_id == Comment.id,
        backref=db.backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False, index=True)
    user = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    report_type = db.Column(
        db.SmallInteger, nullable=False, default=MODERATOR_REPORT_TYPE.SPAM
    )
    reported_at = db.Column(
        db.TIMESTAMP(timezone=True), default=db.func.utcnow(), nullable=False
    )

    __datasets__ = {
        'primary': {'comment', 'user', 'report_type', 'reported_at', 'uuid'}
    }

    @classmethod
    def get_one(cls, exclude_user=None):
        reports = cls.query.filter()
        if exclude_user is not None:
            existing_reports = db.session.query(cls.id).filter_by(
                user_id=exclude_user.id
            )
            reports = reports.filter(~cls.id.in_(existing_reports))

        return reports.order_by(db.func.random()).first()

    @classmethod
    def submit(cls, actor, comment):
        report = cls.query.filter_by(user=actor, comment=comment).one_or_none()
        if report is None:
            report = cls(user=actor, comment=comment)
            db.session.add(report)
        return report

    @with_roles(grants={'site_editor'})
    @property
    def users_who_are_site_editors(self):
        return User.query.join(
            SiteMembership, SiteMembership.user_id == User.id
        ).filter(
            SiteMembership.is_active.is_(True), SiteMembership.is_site_editor.is_(True)
        )
