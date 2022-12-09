"""Project crew notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Optional

from flask import Markup, escape, render_template

from baseframe import _, __

from ...models import (
    Project,
    ProjectCrewMembership,
    ProjectCrewMembershipNotification,
    ProjectCrewMembershipRevokedNotification,
    User,
)
from ...transports.sms import MessageTemplate
from ..helpers import shortlink
from ..notification import RenderNotification


@dataclass
class DecisionFactor:
    """Evaluation criteria for the content of notification (for grants/edits only)."""

    template: str
    is_subject: Optional[bool] = None
    for_actor: Optional[bool] = None
    rtypes: Collection[str] = ()
    is_editor: Optional[bool] = None
    is_promoter: Optional[bool] = None
    is_usher: Optional[bool] = None
    is_actor: Optional[bool] = None

    def match(
        self, is_subject: bool, for_actor: bool, membership: ProjectCrewMembership
    ) -> bool:
        """Test if this :class:`DecisionFactor` is a match."""
        return (
            (self.is_subject is None or self.is_subject is is_subject)
            and (self.for_actor is None or self.for_actor is for_actor)
            and (not self.rtypes or membership.record_type_label.name in self.rtypes)
            and (self.is_editor is None or self.is_editor is membership.is_editor)
            and (self.is_promoter is None or self.is_promoter is membership.is_promoter)
            and (self.is_usher is None or self.is_usher is membership.is_usher)
            and (self.is_actor is None or (self.is_actor is membership.is_self_granted))
        )


# Sequential list of tests, evaluated in order
decision_factors = [
    # --- Subject has been invited by someone (self invite is not possible)
    DecisionFactor(
        template=__(
            "You have been invited to be an editor and promoter of {project} by {actor}"
        ),
        is_subject=True,
        rtypes=['invite'],
        is_editor=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("You have been invited to be an editor of {project} by {actor}"),
        is_subject=True,
        rtypes=['invite'],
        is_editor=True,
    ),
    DecisionFactor(
        template=__("You have been invited to be a promoter of {project} by {actor}"),
        is_subject=True,
        rtypes=['invite'],
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("You have been invited to join the crew of {project} by {actor}"),
        is_subject=True,
        rtypes=['invite'],
    ),
    # --- New person has been invited
    DecisionFactor(
        template=__(
            "{user} has been invited to be an editor and promoter of {project} by"
            " {actor}"
        ),
        rtypes=['invite'],
        is_editor=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{user} has been invited to be an editor of {project} by {actor}"),
        rtypes=['invite'],
        is_editor=True,
    ),
    DecisionFactor(
        template=__("{user} has been invited to be a promoter of {project} by {actor}"),
        rtypes=['invite'],
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{user} has been invited to join the crew of {project} by {actor}"),
        rtypes=['invite'],
    ),
    # --- Subject has accepted an invite (this should NOT trigger a notification)
    DecisionFactor(
        template=__("You have accepted an invite to join the crew of {project}"),
        is_subject=True,
        rtypes=['accept'],
    ),
    # --- Someone has accepted invite
    DecisionFactor(
        template=__(
            "{user} has accepted an invite to be editor and promoter of {project}"
        ),
        rtypes=['accept'],
        is_editor=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{user} has accepted an invite to be editor of {project}"),
        rtypes=['accept'],
        is_editor=True,
    ),
    DecisionFactor(
        template=__("{user} has accepted an invite to be promoter of {project}"),
        rtypes=['accept'],
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{user} has accepted an invite to join the crew of {project}"),
        rtypes=['accept'],
    ),
    # --- Subject has been added to the project
    DecisionFactor(
        template=__("{actor} made you an editor and promoter of {project}"),
        rtypes=['direct_add'],
        is_subject=True,
        is_editor=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{actor} made you an editor of {project}"),
        rtypes=['direct_add'],
        is_subject=True,
        is_editor=True,
    ),
    DecisionFactor(
        template=__("{actor} made you a promoter of {project}"),
        rtypes=['direct_add'],
        is_subject=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{actor} added you to the crew of {project}"),
        rtypes=['direct_add'],
        is_subject=True,
    ),
    # --- Someone has been added to the project
    DecisionFactor(
        template=__("{actor} made {user} an editor and promoter of {project}"),
        rtypes=['direct_add'],
        is_editor=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{actor} made {user} an editor of {project}"),
        rtypes=['direct_add'],
        is_editor=True,
    ),
    DecisionFactor(
        template=__("{actor} made {user} a promoter of {project}"),
        rtypes=['direct_add'],
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{actor} added {user} to the crew of {project}"),
        rtypes=['direct_add'],
    ),
    # --- Subject's roles have changed
    DecisionFactor(
        template=__("You are now an editor and promoter of {project}"),
        rtypes=['amend'],
        is_subject=True,
        is_promoter=True,
        is_editor=True,
    ),
    DecisionFactor(
        template=__("You are now an editor of {project}"),
        rtypes=['amend'],
        is_subject=True,
        is_editor=True,
    ),
    DecisionFactor(
        template=__("You have changed your role to a promoter of {project}"),
        rtypes=['amend'],
        is_subject=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("You have changed your role to be a crew of {project}"),
        rtypes=['amend'],
        is_subject=True,
    ),
    # --- Someone's roles have changed
    DecisionFactor(
        template=__(
            "{user} has changed their role to an editor and promoter of {project}"
        ),
        rtypes=['amend'],
        is_editor=True,
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{user} has changed their role to an editor of {project}"),
        rtypes=['amend'],
        is_editor=True,
    ),
    DecisionFactor(
        template=__("{user} has changed their role to a promoter of {project}"),
        rtypes=['amend'],
        is_promoter=True,
    ),
    DecisionFactor(
        template=__("{user} has changed their role to be a crew of {project}"),
        rtypes=['amend'],
    ),
]


class RenderShared:
    project: Project
    membership: ProjectCrewMembership
    emoji_prefix = "🔑 "
    reason = __("You are receiving this because you are a crew member of a project")

    def activity_template(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> str:
        """Return a Python string template with an appropriate message."""
        raise NotImplementedError("Subclasses must implement `activity_template`")

    def membership_actor(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> Optional[User]:
        """Actor who granted or revoked, for the template."""
        raise NotImplementedError("Subclasses must implement `membership_actor`")

    @property
    def actor(self) -> User:
        """We're interested in who has the membership, not who granted/revoked it."""
        return self.membership.user

    def activity_html(self, membership: Optional[ProjectCrewMembership] = None) -> str:
        """Return HTML rendering of :meth:`activity_template`."""
        if membership is None:
            membership = self.membership
        actor = self.membership_actor(membership)
        return Markup(self.activity_template(membership)).format(
            user=Markup(
                f'<a href="{escape(membership.user.profile_url)}">'
                f'{escape(membership.user.pickername)}</a>'
            )
            if membership.user.profile_url
            else escape(membership.user.pickername),
            project=Markup(
                f'<a href="{escape(self.project.absolute_url)}">'
                f'{escape(self.project.joined_title)}</a>'
            ),
            actor=(
                Markup(
                    f'<a href="{escape(actor.profile_url)}">'
                    f'{escape(actor.pickername)}</a>'
                )
                if actor.profile_url
                else escape(actor.pickername)
            )
            if actor
            else _("(unknown)"),
        )

    def email_subject(self) -> str:
        """Subject line for email."""
        actor = self.membership_actor()
        return self.emoji_prefix + self.activity_template().format(
            user=self.membership.user.pickername,
            project=self.project.joined_title,
            actor=(actor.pickername if actor is not None else _("(unknown)")),
        )

    def sms(self) -> MessageTemplate:
        """SMS notification."""
        actor = self.membership_actor()
        return MessageTemplate(
            message=self.activity_template().format(
                user=self.membership.user.pickername,
                project=self.project.joined_title,
                actor=(actor.pickername if actor is not None else _("(unknown)")),
            )
        )


@ProjectCrewMembershipNotification.renderer
class RenderProjectCrewMembershipNotification(RenderShared, RenderNotification):
    """Render a notification for project crew invite/add/amend."""

    aliases = {'document': 'project', 'fragment': 'membership'}
    fragments_order_by = [ProjectCrewMembership.granted_at.desc()]

    def membership_actor(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> User:
        """Actual actor who granted (or edited) the membership, for the template."""
        return (membership or self.membership).granted_by

    def activity_template(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> str:
        """
        Return a Python string template with an appropriate message.

        Accepts an optional membership object for use in rollups.
        """
        if membership is None:
            membership = self.membership
        membership_user_uuid = membership.user.uuid
        membership_actor = self.membership_actor(membership)
        membership_actor_uuid = membership_actor.uuid if membership_actor else None
        for df in decision_factors:
            if df.match(
                # LHS = user object, RHS = role proxy, so compare uuid
                self.user_notification.user.uuid == membership_user_uuid,
                # Notification is being sent to the actor who caused the notification
                self.user_notification.user.uuid == membership_actor_uuid,
                membership,
            ):
                return df.template
        raise ValueError("No suitable template found for membership record")

    def web(self):
        return render_template(
            'notifications/project_crew_membership_added_web.html.jinja2',
            actor=self.actor,
            view=self,
            project=self.project,
        )

    def email_subject(self):
        return self.emoji_prefix + _(
            "You have been added to {project} as a crew member"
        ).format(project=self.project.joined_title)

    def email_content(self):
        return render_template(
            'notifications/project_crew_membership_added_email.html.jinja2',
            actor=self.actor,
            view=self,
            project=self.project,
        )

    def sms(self) -> MessageTemplate:
        return MessageTemplate(
            message=_("You have been added to {project} as a crew member:").format(
                project=self.project.joined_title
            ),
            url=shortlink(
                self.project.url_for(_external=True, **self.tracking_tags('sms')),
                shorter=True,
            ),
        )


@ProjectCrewMembershipRevokedNotification.renderer
class RenderProjectCrewMembershipRevokedNotification(RenderShared, RenderNotification):
    """Render a notification for project crew revocation."""

    aliases = {'document': 'project', 'fragment': 'membership'}

    def membership_actor(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> Optional[User]:
        """Actual actor who revoked the membership, for the template."""
        return (membership or self.membership).revoked_by

    def activity_template(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> str:
        """Return a single line summary of changes."""
        if membership is None:
            membership = self.membership
        # LHS = user object, RHS = role proxy, so compare uuid
        if self.user_notification.user.uuid == membership.user.uuid:
            if membership.user == membership.revoked_by:
                return _("You removed yourself as a crew member of {project}")
            return _("You were removed as crew member of {project} by {actor}")
        return _("{user} was removed as a crew member of {project} by {actor}")

    def web(self) -> str:
        """Render for web."""
        return render_template(
            'notifications/project_crew_membership_revoked_web.html.jinja2', view=self
        )

    def email_content(self) -> str:
        """Render email content."""
        return render_template(
            'notifications/project_crew_membership_revoked_email.html.jinja2', view=self
        )
