from flask import Markup, escape, render_template, url_for
from werkzeug.utils import cached_property

from baseframe import _, __

from ...models import (
    CommentReplyNotification,
    CommentReportReceivedNotification,
    ProjectCommentNotification,
    ProposalCommentNotification,
)
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


@CommentReplyNotification.renderer
@ProjectCommentNotification.renderer
@ProposalCommentNotification.renderer
class CommentNotification(RenderNotification):
    """Render comment notifications for various document types."""

    aliases = {'fragment': 'comment'}
    emoji_prefix = "💬 "

    @property
    def actor(self):
        """The actor who commented."""
        return self.comment.user

    @cached_property
    def commenters(self):
        # A set comprehension would have been simpler, but RoleAccessProxy isn't
        # hashable. Else: ``return {_c.user for _c in self.fragments}``
        user_ids = set()
        users = []
        for comment in self.fragments:
            if comment.user.uuid not in user_ids:
                users.append(comment.user)
                user_ids.add(comment.user.uuid)
        return users

    @property
    def document_type(self):
        return self.notification.document_model.__tablename__

    def document_comments_url(self, **kwargs):
        if self.document_type == 'project':
            return self.document.url_for('comments', **kwargs)
        if self.document_type == 'proposal':
            return self.document.url_for('view', **kwargs) + '#comments'
        return self.document.url_for('view', **kwargs)

    def activity_template_standalone(self, comment=None):
        if comment is None:
            comment = self.comment
        if self.document_type == 'comment':
            return _("{actor} replied to your comment")
        if self.document_type == 'project':
            return _("{actor} commented on your project")
        if self.document_type == 'proposal':
            return _("{actor} commented on your proposal")

    def activity_template_inline(self, comment=None):
        if comment is None:
            comment = self.comment
        if self.document_type == 'comment':
            return _("{actor} replied to your comment:")
        if self.document_type == 'project':
            return _("{actor} commented on your project:")
        if self.document_type == 'proposal':
            return _("{actor} commented on your proposal:")

    def activity_html(self, comment=None):
        if not comment:
            comment = self.comment
        return Markup(self.activity_template_inline(comment)).format(
            actor=Markup(
                '<a href="{url}">{name}</a>'.format(
                    url=escape(self.actor.profile_url),
                    name=escape(self.actor.pickername),
                )
            )
            if self.actor.profile_url
            else escape(self.actor.pickername),
        )

    def web(self):
        return render_template(
            'notifications/comment_received_web.html.jinja2',
            view=self,
            is_rollup=self.is_rollup,
        )

    def email_subject(self):
        return self.emoji_prefix + self.activity_template_standalone().format(
            actor=self.actor.pickername
        )

    def email_content(self):
        return render_template(
            'notifications/comment_received_email.html.jinja2', view=self
        )

    def sms(self):
        return (
            self.activity_template_inline().format(actor=self.actor.pickername)
            + " "
            + shortlink(self.comment.url_for(_external=True))
        )
