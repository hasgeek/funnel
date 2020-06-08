from baseframe import __
from coaster.utils import LabeledEnum

from . import Comment, IdMixin, User, UuidMixin, db

__all__ = ['MODERATOR_REPORT_TYPE', 'CommentModeratorReport']


class MODERATOR_REPORT_TYPE(LabeledEnum):  # NOQA: N801
    OK = (0, 'ok', __("OK"))
    SPAM = (1, 'spam', __("Spam"))


class CommentModeratorReport(IdMixin, UuidMixin, db.Model):
    __tablename__ = 'comment_moderator_report'
    __uuid_primary_key__ = True

    reported_by_id = db.Column(
        None, db.ForeignKey('user.id'), nullable=False, index=True
    )
    reported_by = db.relationship(
        User,
        primaryjoin=reported_by_id == User.id,
        backref=db.backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    comment_id = db.Column(
        None, db.ForeignKey('comment.id'), nullable=False, index=True
    )
    comment = db.relationship(
        Comment,
        primaryjoin=comment_id == Comment.id,
        backref=db.backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    report_type = db.Column(
        db.SmallInteger, nullable=False, default=MODERATOR_REPORT_TYPE.SPAM
    )

    @classmethod
    def get_one(cls, exclude_reported_by=None):
        reports = cls.query.filter()
        if exclude_reported_by is not None:
            reports = reports.filter(cls.reported_by != exclude_reported_by)
        return reports.order_by(db.func.random()).first()


def _report_comment(self, reported_by):
    report = CommentModeratorReport.query.filter_by(
        reported_by=reported_by, comment=self
    ).one_or_none()
    if report is None:
        report = CommentModeratorReport(reported_by=reported_by, comment=self)
        db.session.add(report)
        db.session.commit()
    return report


Comment.report_spam = _report_comment
