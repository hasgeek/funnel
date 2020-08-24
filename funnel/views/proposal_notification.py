from flask import render_template

from baseframe import _

from ..models import ProposalReceivedNotification, ProposalSubmittedNotification
from .notification import RenderNotification


@ProposalReceivedNotification.renderer
class RenderProposalReceivedNotification(RenderNotification):
    """Notify the project editor when a new proposal is submitted."""

    # self.document is Rsvp instance

    def web(self):
        return render_template(
            'notifications/proposal_received_web.html.jinja2',
            view=self,
            proposal=self.document,
            project=self.document.project,
        )

    def email_subject(self):
        return _("New proposal for {project}: {proposal}").format(
            proposal=self.document, project=self.document.project.title
        )

    def email_content(self):
        # FIXME: Move into folder, rename to match notification type, and use 'actor'
        return render_template(
            'notifications/proposal_received_email.html.jinja2',
            view=self,
            actor=self.document.user,
            proposal=self.document,
            project=self.document.project,
        )

    def sms(self):
        return _("New proposal for {project}: {proposal}").format(
            proposal=self.document.title, project=self.document.project.title,
        )


@ProposalSubmittedNotification.renderer
class RenderProposalSubmittedNotification(RenderNotification):
    """Notify the participant when they cancel registration."""

    # self.document is Rsvp instance

    def web(self):
        return render_template(
            'notifications/proposal_submitted_web.html.jinja2',
            view=self,
            proposal=self.document,
            project=self.document.project,
        )

    def email_subject(self):
        return _("Proposal submitted for {project}: {proposal}").format(
            project=self.document.project.title, proposal=self.document.title,
        )

    def email_content(self):
        return render_template(
            'notifications/proposal_submitted_email.html.jinja2',
            view=self,
            actor=self.document.user,
            proposal=self.document,
            project=self.document.project,
        )
