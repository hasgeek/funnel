from __future__ import annotations

from baseframe import __
from coaster.sqlalchemy import with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, Comment, SiteMembership, User, UuidMixin, db
from .helpers import reopen

__all__ = ['MODERATOR_REPORT_TYPE', 'CommentModeratorReport']


class MODERATOR_REPORT_TYPE(LabeledEnum):
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
    resolved_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)

    __datasets__ = {
        'primary': {
            'comment',
            'user',
            'report_type',
            'reported_at',
            'resolved_at',
            'uuid',
        }
    }

    @classmethod
    def get_one(cls, exclude_user=None):
        reports = cls.get_all(exclude_user)
        return reports.order_by(db.func.random()).first()

    @classmethod
    def get_all(cls, exclude_user=None):
        """
        Get all reports.

        If ``exclude_user`` is provided, exclude all reports for
        the comments that the given user has already reviewed/reported.
        """
        reports = cls.query.filter(cls.resolved_at.is_(None))
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

    @classmethod
    def submit(cls, actor, comment):
        created = False
        report = cls.query.filter_by(user=actor, comment=comment).one_or_none()
        if report is None:
            report = cls(user=actor, comment=comment)
            db.session.add(report)
            created = True
        return report, created

    @property
    def users_who_are_comment_moderators(self):
        return User.query.join(
            SiteMembership, SiteMembership.user_id == User.id
        ).filter(
            SiteMembership.is_active.is_(True),
            SiteMembership.is_comment_moderator.is_(True),
        )

    with_roles(users_who_are_comment_moderators, grants={'comment_moderator'})


@reopen(Comment)
class __Comment:
    def is_reviewed_by(self, user: User) -> bool:
        return db.session.query(
            db.session.query(CommentModeratorReport)
            .filter(
                CommentModeratorReport.comment == self,
                CommentModeratorReport.resolved_at.is_(None),
                CommentModeratorReport.user == user,
            )
            .exists()
        ).scalar()
