from flask import render_template

from baseframe import _

from ..models import (
    Proposal,
    ProposalReceivedNotification,
    ProposalSubmittedNotification,
    db,
)
from .notification import RenderNotification


@ProposalReceivedNotification.renderer
class RenderProposalReceivedNotification(RenderNotification):
    """Notify the project editor when a new proposal is submitted."""

    aliases = {'document': 'project', 'fragment': 'proposal'}

    def web(self):
        proposals = (
            self.user_notification.rolledup_fragments()
            .options(
                db.load_only(
                    Proposal.name, Proposal.title, Proposal.project_id, Proposal.uuid
                )
            )
            .order_by(Proposal.datetime.desc())
            .all()
        )
        return render_template(
            'notifications/proposal_received_web.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.project,
            is_rollup=len(proposals) > 1,
            proposals=proposals,
        )

    def email_subject(self):
        return _("New proposal for {project}: {proposal}").format(
            proposal=self.proposal, project=self.project.joined_title
        )

    def email_content(self):
        return render_template(
            'notifications/proposal_received_email.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.project,
        )

    def sms(self):
        return _("New proposal for {project}: {proposal} {url}").format(
            proposal=self.proposal.title,
            project=self.project.joined_title,
            url=self.proposal.url_for(_external=True),
        )


@ProposalSubmittedNotification.renderer
class RenderProposalSubmittedNotification(RenderNotification):
    """Notify the proposer that their proposal has been submitted."""

    aliases = {'document': 'proposal'}

    def web(self):
        return render_template(
            'notifications/proposal_submitted_web.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.proposal.project,
        )

    def email_subject(self):
        return _("Proposal submitted for {project}: {proposal}").format(
            project=self.proposal.project.joined_title, proposal=self.proposal.title,
        )

    def email_content(self):
        return render_template(
            'notifications/proposal_submitted_email.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.proposal.project,
        )

    def sms(self):
        return _("Your proposal has been submitted to {project} {url}").format(
            project=self.proposal.project.joined_title,
            url=self.proposal.url_for(_external=True),
        )
