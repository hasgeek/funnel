from baseframe import __
from coaster.utils import LabeledEnum

from . import BaseMixin, Comment, User, UuidMixin, db

__all__ = ['MODERATOR_REPORT_TYPE', 'CommentModeratorReport']


class MODERATOR_REPORT_TYPE(LabeledEnum):  # NOQA: N801
    OK = (0, 'ok', __("OK"))
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
        db.TIMESTAMP(timezone=True), default=db.func.utcnow(), nullable=False,
    )

    @classmethod
    def get_one(cls, exclude_user=None):
        reports = cls.query.filter()
        if exclude_user is not None:
            reports = reports.filter(cls.user != exclude_user)
        return reports.order_by(db.func.random()).first()


def _report_comment(self, actor):
    report = CommentModeratorReport.query.filter_by(
        user=actor, comment=self
    ).one_or_none()
    if report is None:
        report = CommentModeratorReport(user=actor, comment=self)
        db.session.add(report)
        db.session.commit()
    return report


Comment.report_spam = _report_comment
