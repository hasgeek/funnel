from baseframe import __
from coaster.utils import LabeledEnum

from . import BaseMixin, Comment, User, UuidMixin, db

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
        db.TIMESTAMP(timezone=True), default=db.func.utcnow(), nullable=False,
    )

    @classmethod
    def get_one(cls, exclude_user=None):
        reports = cls.get_all(exclude_user)
        return reports.order_by(db.func.random()).first()

    @classmethod
    def get_all(cls, exclude_user=None):
        """
        Get all reports.

        If ``exclude_user`` is provided, exclude all reports for
        the comments that the given user has reviewed/reported.
        """
        reports = cls.query.filter()
        if exclude_user is not None:
            # get all comment ids that the given user has already reviewed/reported
            existing_reported_comments = (
                db.session.query(cls.comment_id)
                .filter_by(user_id=exclude_user.id)
                .distinct()
            )
            # exclude reports for those comments
            reports = reports.filter(~cls.comment_id.in_(existing_reported_comments))
        return reports


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
