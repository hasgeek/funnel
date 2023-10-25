"""̌Comment noficiations."""

from __future__ import annotations

from flask import render_template, url_for
from markupsafe import Markup, escape
from werkzeug.utils import cached_property

from baseframe import _, __

from ...models import (
    Account,
    Comment,
    CommentModeratorReport,
    CommentReplyNotification,
    CommentReportReceivedNotification,
    Commentset,
    DuckTypeAccount,
    NewCommentNotification,
    Project,
    Proposal,
)
from ...transports.sms import OneLineTemplate, SmsPriority, SmsTemplate
from ..helpers import shortlink
from ..notification import RenderNotification
from .mixins import TemplateVarMixin


class CommentReplyTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for a reply to a comment."""

    registered_template = (
        '{#var#} has replied to your comment: {#var#}'
        '\n\nhttps://bye.li to stop -Hasgeek'
    )
    template = (
        '{actor} has replied to your comment: {url}'
        '\n\nhttps://bye.li to stop -Hasgeek'
    )
    plaintext_template = '{actor} has replied to your comment: {url}'
    message_priority = SmsPriority.NORMAL

    url: str


class CommentProposalTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for a comment on a proposal."""

    registered_template = (
        '{#var#} commented on your submission: {#var#}'
        '\n\nhttps://bye.li to stop -Hasgeek'
    )
    template = (
        '{actor} commented on your submission: {url}'
        '\n\nhttps://bye.li to stop -Hasgeek'
    )
    plaintext_template = '{actor} commented on your submission: {url}'
    message_priority = SmsPriority.NORMAL

    url: str


class CommentProjectTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for a comment on a project."""

    registered_template = (
        '{#var#} commented on a project you are in: {#var#}'
        '\n\nhttps://bye.li to stop -Hasgeek'
    )
    template = (
        '{actor} commented on a project you are in: {url}'
        '\n\nhttps://bye.li to stop -Hasgeek'
    )
    plaintext_template = '{actor} commented on a project you are in: {url}'
    message_priority = SmsPriority.NORMAL

    url: str


@CommentReportReceivedNotification.renderer
class RenderCommentReportReceivedNotification(RenderNotification):
    """Notify site admins when a comment report is received."""

    comment: Comment
    report: CommentModeratorReport
    aliases = {'document': 'comment', 'fragment': 'report'}
    emoji_prefix = "💩 "
    reason = __("You are receiving this because you are a site admin")
    hero_image = 'img/email/chars-v1/admin-report.png'
    email_heading = __("Spam alert!")

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
                ),
                shorter=True,
            ),
        )


@CommentReplyNotification.renderer
@NewCommentNotification.renderer
class CommentNotification(RenderNotification):
    """Render comment notifications for various document types."""

    document: Commentset | Comment
    comment: Comment
    aliases = {'fragment': 'comment'}
    emoji_prefix = "💬 "
    hero_image = 'img/email/chars-v1/comment.png'
    email_heading = __("New comment!")

    @property
    def actor(self) -> Account | DuckTypeAccount:
        """Actor who commented."""
        return self.comment.posted_by

    @cached_property
    def commenters(self) -> list[Account]:
        """List of unique users from across rolled-up comments. Could be singular."""
        # A set comprehension would have been simpler, but RoleAccessProxy isn't
        # hashable. Else: ``return {_c.posted_by for _c in self.fragments}``
        # TODO: Reconfirm above as RoleAccessProxy has changed to be more transparent
        posted_by_ids = set()
        comment_posters = []
        for comment in self.fragments:  # pylint: disable=not-an-iterable
            if comment.posted_by.uuid not in posted_by_ids:
                comment_posters.append(comment.posted_by)
                posted_by_ids.add(comment.posted_by.uuid)
        return comment_posters

    @property
    def project(self) -> Project | None:
        if self.document_type == 'project':
            return self.document.project
        if self.document_type == 'proposal':
            return self.document.proposal.project
        return None

    @property
    def proposal(self) -> Proposal | None:
        if self.document_type == 'proposal':
            return self.document.proposal
        return None

    @property
    def document_type(self) -> str:
        """Return type of document this comment is on ('comment' for replies)."""
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

    def activity_template_standalone(self, comment: Comment | None = None) -> str:
        """Activity template for standalone use, such as email subject."""
        if comment is None:
            comment = self.comment
        if self.document_type == 'comment':
            return _("{actor} replied to your comment in {project}")
        if self.document_type == 'project':
            return _("{actor} commented in {project}")
        if self.document_type == 'proposal':
            return _("{actor} commented on {proposal}")
        # Unknown document type
        return _("{actor} replied to you")

    def activity_template_inline(self, comment: Comment | None = None) -> str:
        """Activity template for inline use with other content, like SMS with URL."""
        if comment is None:
            comment = self.comment
        if self.document_type == 'comment':
            return _("{actor} replied to your comment in {project}:")
        if self.document_type == 'project':
            return _("{actor} commented in {project}:")
        if self.document_type == 'proposal':
            return _("{actor} commented on {proposal}:")
        # Unknown document type
        return _("{actor} replied to you:")

    def activity_html(self, comment: Comment | None = None) -> str:
        """Activity template rendered into HTML, for use in web and email templates."""
        if comment is None:
            comment = self.comment

        actor_markup = (
            Markup(
                f'<a href="{escape(self.actor.absolute_url)}">'
                f'{escape(self.actor.pickername)}</a>'
            )
            if self.actor.absolute_url
            else escape(self.actor.pickername)
        )
        project = self.project
        project_markup = (
            Markup(
                f'<a href="{escape(project.absolute_url)}">'
                f'{escape(project.joined_title)}</a>'
            )
            if project is not None
            else Markup('')
        )
        proposal = self.proposal
        proposal_markup = (
            Markup(
                f'<a href="{escape(proposal.absolute_url)}">'
                f'{escape(proposal.title)}</a>'
            )
            if proposal is not None
            else Markup('')
        )

        return Markup(self.activity_template_inline(comment)).format(
            actor=actor_markup,
            project=project_markup,
            proposal=proposal_markup,
        )

    def web(self) -> str:
        return render_template(
            'notifications/comment_received_web.html.jinja2',
            view=self,
            is_rollup=self.is_rollup,
        )

    def email_subject(self) -> str:
        project = self.project
        proposal = self.proposal
        return self.emoji_prefix + self.activity_template_standalone().format(
            actor=self.actor.pickername,
            project=project.joined_title if project else '',
            proposal=proposal.title if proposal else '',
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/comment_received_email.html.jinja2', view=self
        )

    def sms(self):
        url = shortlink(
            self.comment.url_for(_external=True, **self.tracking_tags('sms'))
        )
        if self.document_type == 'comment':
            return CommentReplyTemplate(actor=self.actor, url=url)
        if self.document_type == 'project':
            return CommentProjectTemplate(actor=self.actor, url=url)
        if self.document_type == 'proposal':
            return CommentProposalTemplate(actor=self.actor, url=url)
        # Unknown document type
        return CommentReplyTemplate(actor=self.actor, url=url)
