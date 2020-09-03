from flask import render_template, url_for

from baseframe import _, __

from ...models import CommentReportReceivedNotification
from ..helpers import shortlink
from ..notification import RenderNotification


@CommentReportReceivedNotification.renderer
class RenderCommentReportReceivedNotification(RenderNotification):
    """Notify site admins when a comment report is received."""

    aliases = {'document': 'comment', 'fragment': 'report'}
    emoji_prefix = "💩 "
    reason = __("You are receiving this because you are a site admin")

    def web(self):
        return render_template(
            'notifications/comment_report_received_web.html.jinja2', view=self
        )

    def email_subject(self):
        return self.emoji_prefix + _("A comment has been reported as spam")

    def email_content(self):
        return render_template(
            'notifications/comment_report_received_email.html.jinja2', view=self
        )

    def sms(self):
        return _("A comment has been reported as spam. {url}").format(
            url=shortlink(
                url_for('siteadmin_review_comment', report=self.report.uuid_b58)
            )
        )
