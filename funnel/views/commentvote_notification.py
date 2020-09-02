from flask import render_template

from baseframe import _, __

from ..models import CommentReportReceivedNotification
from .notification import RenderNotification


@CommentReportReceivedNotification.renderer
class RenderCommentReportReceivedNotification(RenderNotification):
    """Notify site admins when a comment report is received."""

    aliases = {'document': 'comment', 'fragment': 'report'}

    reason = __("You are receiving this because you are a site admin.")

    def web(self):
        return render_template(
            'notifications/comment_report_received_web.html.jinja2', view=self
        )

    def email_subject(self):
        return _("Comment reported as spam")

    def email_content(self):
        return render_template(
            'notifications/comment_report_received_email.html.jinja2', view=self
        )
