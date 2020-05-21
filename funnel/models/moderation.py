from baseframe import __
from coaster.utils import LabeledEnum

from . import Comment, NoIdMixin, User, UuidMixin, db

__all__ = ['MODERATOR_REPORT_TYPE', 'CommentModeratorReport']


class MODERATOR_REPORT_TYPE(LabeledEnum):  # NOQA: N801
    SPAM = (0, 'spam', __("Spam"))


class CommentModeratorReport(UuidMixin, NoIdMixin, db.Model):
    __tablename__ = 'comment_moderator_report'

    user_id = db.Column(
        None, db.ForeignKey('user.id'), nullable=False, primary_key=True
    )
    user = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    comment_id = db.Column(
        None, db.ForeignKey('comment.id'), nullable=False, primary_key=True
    )
    comment = db.relationship(
        Comment,
        primaryjoin=comment_id == Comment.id,
        backref=db.backref('moderator_reports', cascade='all', lazy='dynamic'),
    )
    report_type = db.Column(
        db.SmallInteger, nullable=False, default=MODERATOR_REPORT_TYPE.SPAM
    )
