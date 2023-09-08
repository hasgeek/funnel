"""Site moderator models."""

from __future__ import annotations

from baseframe import __
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, Mapped, Model, UuidMixin, backref, db, relationship, sa
from .account import Account
from .comment import Comment
from .helpers import reopen
from .site_membership import SiteMembership

__all__ = ['MODERATOR_REPORT_TYPE', 'CommentModeratorReport']


class MODERATOR_REPORT_TYPE(LabeledEnum):  # noqa: N801
    OK = (1, 'ok', __("Not spam"))
    SPAM = (2, 'spam', __("Spam"))


class CommentModeratorReport(UuidMixin, BaseMixin, Model):
    __tablename__ = 'comment_moderator_report'
    __uuid_primary_key__ = True

    comment_id = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('comment.id'), nullable=False, index=True
    )
    comment: Mapped[Comment] = relationship(
        Comment,
        foreign_keys=[comment_id],
        backref=backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    reported_by_id: Mapped[int] = sa.orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False, index=True
    )
    reported_by: Mapped[Account] = relationship(
        Account,
        foreign_keys=[reported_by_id],
        backref=backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    report_type = sa.orm.mapped_column(
        sa.SmallInteger,
        StateManager.check_constraint('report_type', MODERATOR_REPORT_TYPE),
        nullable=False,
        default=MODERATOR_REPORT_TYPE.SPAM,
    )
    reported_at = sa.orm.mapped_column(
        sa.TIMESTAMP(timezone=True), default=sa.func.utcnow(), nullable=False
    )
    resolved_at = sa.orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True, index=True
    )

    __datasets__ = {
        'primary': {
            'comment',
            'reported_by',
            'report_type',
            'reported_at',
            'resolved_at',
            'uuid',
        }
    }

    @classmethod
    def get_one(cls, exclude_user=None):
        reports = cls.get_all(exclude_user)
        return reports.order_by(sa.func.random()).first()

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
                .filter_by(reported_by_id=exclude_user.id)
                .distinct()
            )
            # exclude reports for those comments
            reports = reports.filter(~cls.comment_id.in_(existing_reported_comments))
        return reports

    @classmethod
    def submit(
        cls, actor: Account, comment: Comment
    ) -> tuple[CommentModeratorReport, bool]:
        created = False
        report = cls.query.filter_by(reported_by=actor, comment=comment).one_or_none()
        if report is None:
            report = cls(reported_by=actor, comment=comment)
            db.session.add(report)
            created = True
        return report, created

    @property
    def users_who_are_comment_moderators(self):
        return Account.query.join(
            SiteMembership, SiteMembership.member_id == Account.id
        ).filter(
            SiteMembership.is_active.is_(True),
            SiteMembership.is_comment_moderator.is_(True),
        )

    with_roles(users_who_are_comment_moderators, grants={'comment_moderator'})


@reopen(Comment)
class __Comment:
    def is_reviewed_by(self, account: Account) -> bool:
        return db.session.query(
            db.session.query(CommentModeratorReport)
            .filter(
                CommentModeratorReport.comment == self,
                CommentModeratorReport.resolved_at.is_(None),
                CommentModeratorReport.reported_by == account,
            )
            .exists()
        ).scalar()
