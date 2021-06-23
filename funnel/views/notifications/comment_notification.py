from __future__ import annotations

from typing import List, Optional

from flask import Markup, escape, render_template, url_for
from werkzeug.utils import cached_property

from baseframe import _, __

from ...models import (
    Comment,
    CommentModeratorReport,
    CommentReplyNotification,
    CommentReportReceivedNotification,
    NewCommentNotification,
    User,
)
from ...transports.sms import OneLineTemplate
from ..helpers import shortlink
from ..notification import RenderNotification


@CommentReportReceivedNotification.renderer
class RenderCommentReportReceivedNotification(RenderNotification):
    """Notify site admins when a comment report is received."""

    comment: Comment
    report: CommentModeratorReport
    aliases = {'document': 'comment', 'fragment': 'report'}
    emoji_prefix = "💩 "
    reason = __("You are receiving this because you are a site admin")

    def web(self) -> str:
        return render_template(
            'notifications/comment_report_received_web.html.jinja2', view=self
        )

    def email_subject(self) -> str:
        return self.emoji_prefix + _("A comment has been reported as spam")

    def email_content(self) -> str:
        return render_template(
            'notifications/comment_report_received_email.html.jinja2', view=self
        )

    def sms(self) -> OneLineTemplate:
        return OneLineTemplate(
            text1=_("A comment has been reported as spam."),
            url=shortlink(
                url_for(
                    'siteadmin_review_comment',
                    report=self.report.uuid_b58,
                    _external=True,
                    **self.tracking_tags('sms'),
                )
            ),
        )


@CommentReplyNotification.renderer
@NewCommentNotification.renderer
class CommentNotification(RenderNotification):
    """Render comment notifications for various document types."""

    comment: Comment
    aliases = {'fragment': 'comment'}
    emoji_prefix = "💬 "

    @property
    def actor(self) -> User:
        """Actor who commented."""
        return self.comment.user

    @cached_property
    def commenters(self) -> List[User]:
        """List of unique users from across rolled-up comments. Could be singular."""
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
    def document_type(self) -> str:
        if self.notification.document_type == 'comment':
            return 'comment'
        return self.document.parent_type

    def document_comments_url(self, **kwargs) -> str:
        """URL to comments view on the document."""
        if self.document_type == 'project':
            return self.document.parent.url_for('comments', **kwargs)
        if self.document_type == 'proposal':
            return self.document.parent.url_for('view', **kwargs) + '#comments'
        return self.document.url_for('view', **kwargs)

    def activity_template_standalone(self, comment: Optional[Comment] = None) -> str:
        """Activity template for standalone use, such as email subject."""
        if comment is None:
            comment = self.comment
        if self.document_type == 'comment':
            return _("{actor} replied to your comment")
        if self.document_type == 'project':
            return _("{actor} commented on a project you are in")
        if self.document_type == 'proposal':
            return _("{actor} commented on your submission")
        # Unknown document type
        return _("{actor} replied to you")

    def activity_template_inline(self, comment: Optional[Comment] = None) -> str:
        """Activity template for inline use with other content, like SMS with URL."""
        if comment is None:
            comment = self.comment
        if self.document_type == 'comment':
            return _("{actor} replied to your comment:")
        if self.document_type == 'project':
            return _("{actor} commented on a project you are in:")
        if self.document_type == 'proposal':
            return _("{actor} commented on your submission:")
        # Unknown document type
        return _("{actor} replied to you:")

    def activity_html(self, comment: Optional[Comment] = None) -> str:
        """Activity template rendered into HTML, for use in web and email templates."""
        if comment is None:
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

    def web(self) -> str:
        return render_template(
            'notifications/comment_received_web.html.jinja2',
            view=self,
            is_rollup=self.is_rollup,
        )

    def email_subject(self) -> str:
        return self.emoji_prefix + self.activity_template_standalone().format(
            actor=self.actor.pickername
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/comment_received_email.html.jinja2', view=self
        )

    def sms(self) -> OneLineTemplate:
        return OneLineTemplate(
            text1=self.activity_template_inline().format(actor=self.actor.pickername),
            url=shortlink(
                self.comment.url_for(_external=True, **self.tracking_tags('sms'))
            ),
        )
