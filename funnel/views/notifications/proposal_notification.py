from __future__ import annotations

from flask import render_template

from baseframe import _, __

from ...models import (
    Project,
    Proposal,
    ProposalReceivedNotification,
    ProposalSubmittedNotification,
    db,
)
from ...transports.sms import TwoLineTemplate
from ..helpers import shortlink
from ..notification import RenderNotification


@ProposalReceivedNotification.renderer
class RenderProposalReceivedNotification(RenderNotification):
    """Notify the project editor when a new proposal is submitted."""

    project: Project
    proposal: Proposal
    aliases = {'document': 'project', 'fragment': 'proposal'}
    emoji_prefix = "📥 "
    reason = __("You are receiving this because you are an editor of this project")

    fragments_order_by = [Proposal.datetime.desc()]
    fragments_query_options = [
        db.load_only(Proposal.name, Proposal.title, Proposal.project_id, Proposal.uuid)
    ]

    def web(self):
        return render_template(
            'notifications/proposal_received_web.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.project,
        )

    def email_subject(self):
        return self.emoji_prefix + _("New submission in {project}: {proposal}").format(
            proposal=self.proposal.title, project=self.project.joined_title()
        )

    def email_content(self):
        return render_template(
            'notifications/proposal_received_email.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.project,
        )

    def sms(self) -> TwoLineTemplate:
        return TwoLineTemplate(
            text1=_("New submission in {project}:").format(
                project=self.project.joined_title('>')
            ),
            text2=self.proposal.title,
            url=shortlink(
                self.proposal.url_for(_external=True, **self.tracking_tags('sms'))
            ),
        )


@ProposalSubmittedNotification.renderer
class RenderProposalSubmittedNotification(RenderNotification):
    """Notify the proposer that their proposal has been submitted."""

    proposal: Proposal
    aliases = {'document': 'proposal'}
    emoji_prefix = "📤 "
    reason = __("You are receiving this because you made this submission")

    def web(self):
        return render_template(
            'notifications/proposal_submitted_web.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.proposal.project,
        )

    def email_subject(self):
        return self.emoji_prefix + _("Submission made to {project}: {proposal}").format(
            project=self.proposal.project.joined_title(), proposal=self.proposal.title
        )

    def email_content(self):
        return render_template(
            'notifications/proposal_submitted_email.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.proposal.project,
        )

    def sms(self) -> TwoLineTemplate:
        return TwoLineTemplate(
            text1=_("Your submission has been received in {project}:").format(
                project=self.proposal.project.joined_title('>')
            ),
            text2=self.proposal.title,
            url=shortlink(
                self.proposal.url_for(_external=True, **self.tracking_tags('sms'))
            ),
        )
