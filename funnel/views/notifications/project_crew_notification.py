"""Project crew notifications."""

from __future__ import annotations

from flask import render_template

from baseframe import _, __

from ...models import Project, ProjectCrewMembershipNotification
from ...transports.sms import TwoLineTemplate
from ..helpers import shortlink
from ..notification import RenderNotification


@ProjectCrewMembershipNotification.renderer
class RenderProjectCrewMembershipNotification(RenderNotification):
    project: Project
    aliases = {'document': 'project'}
    emoji_prefix = "📥 "
    reason = __(
        "You are receiving this because you are added as a crew member of this project"
    )

    def web(self):
        return render_template(
            'notifications/proposal_received_web.html.jinja2',
            view=self,
            proposal=self.proposal,
            project=self.project,
        )

    def email_subject(self):
        return self.emoji_prefix + _(
            "You have been added to {project} as a crew member"
        ).format(project=self.joined_title())

    def email_content(self):
        return render_template(
            'email_project_crew_membership_add_notification.html.jinja2',
            actor='',  # TODO
            project=self.obj,
            membership='',  # TODO
        )

    def sms(self) -> TwoLineTemplate:
        return TwoLineTemplate(
            text1=_("You have been added to {project} as a crew member:").format(
                project=self.project.joined_title('>')
            ),
            text2=self.project.title,
            url=shortlink(
                self.project.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )
