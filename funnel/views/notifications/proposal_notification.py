"""Proposal (submission) notifications."""

from __future__ import annotations

from flask import render_template

from baseframe import _, __

from ...models import (
    Project,
    Proposal,
    ProposalReceivedNotification,
    ProposalSubmittedNotification,
    sa,
)
from ...transports.sms import SmsTemplate
from ..helpers import shortlink
from ..notification import RenderNotification
from .mixins import TemplateVarMixin


class ProposalReceivedTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for Proposal received."""

    registered_template = (
        "There's a new submission from {#var#} in {#var#}."
        " Read it here: {#var#}\n\nhttps://bye.li to stop -Hasgeek"
    )
    template = (
        "There's a new submission from {actor} in {project}."
        " Read it here: {url}\n\nhttps://bye.li to stop -Hasgeek"
    )
    plaintext_template = (
        "There's a new submission from {actor} in {project}. Read it here: {url}"
    )

    actor: str
    url: str


class ProposalSubmittedTemplate(TemplateVarMixin, SmsTemplate):
    """DLT registered template for Proposal submitted."""

    registered_template = (
        "{#var#} has received your submission. Here's the link to share: {#var#}"
        "\n\nhttps://bye.li to stop -Hasgeek"
    )
    template = (
        "{project} has received your submission. Here's the link to share: {url}"
        "\n\nhttps://bye.li to stop -Hasgeek"
    )
    plaintext_template = (
        "{project} has received your submission. Here's the link to share: {url}"
    )

    url: str


@ProposalReceivedNotification.renderer
class RenderProposalReceivedNotification(RenderNotification):
    """Notify the project editor when a new proposal is submitted."""

    project: Project
    proposal: Proposal
    aliases = {'document': 'project', 'fragment': 'proposal'}
    emoji_prefix = "📥 "
    reason = __("You are receiving this because you are an editor of this project")
    hero_image = 'img/email/chars-v1/new-submission.png'
    email_heading = __("New submission!")

    fragments_order_by = [Proposal.datetime.desc()]
    fragments_query_options = [
        sa.orm.load_only(
            Proposal.name, Proposal.title, Proposal.project_id, Proposal.uuid
        )
    ]

    def web(self) -> str:
        return render_template(
            'notifications/proposal_received_web.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.project,
        )

    def email_subject(self) -> str:
        return self.emoji_prefix + _("New submission in {project}: {proposal}").format(
            proposal=self.proposal.title, project=self.project.joined_title
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/proposal_received_email.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.project,
        )

    def sms(self) -> ProposalReceivedTemplate:
        return ProposalReceivedTemplate(
            project=self.project,
            actor=self.proposal.user,
            url=shortlink(
                self.proposal.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )


@ProposalSubmittedNotification.renderer
class RenderProposalSubmittedNotification(RenderNotification):
    """Notify the proposer that their proposal has been submitted."""

    proposal: Proposal
    aliases = {'document': 'proposal'}
    emoji_prefix = "📤 "
    reason = __("You are receiving this because you made this submission")
    hero_image = 'img/email/chars-v1/sent-submission.png'
    email_heading = __("Proposal sumbitted!")

    def web(self) -> str:
        return render_template(
            'notifications/proposal_submitted_web.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.proposal.project,
        )

    def email_subject(self) -> str:
        return self.emoji_prefix + _("Submission made to {project}: {proposal}").format(
            project=self.proposal.project.joined_title, proposal=self.proposal.title
        )

    def email_content(self) -> str:
        return render_template(
            'notifications/proposal_submitted_email.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.proposal.project,
        )

    def sms(self) -> ProposalSubmittedTemplate:
        return ProposalSubmittedTemplate(
            project=self.proposal.project,
            url=shortlink(
                self.proposal.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
