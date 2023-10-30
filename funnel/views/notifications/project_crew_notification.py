"""Project crew notifications."""

from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import ClassVar

from flask import render_template
from markupsafe import Markup, escape

from baseframe import _, __

from ...models import (
    Account,
    NotificationRecipient,
    NotificationType,
    Project,
    ProjectCrewMembershipNotification,
    ProjectCrewMembershipRevokedNotification,
    ProjectMembership,
)
from ...transports.sms import OneLineTemplate
from ..helpers import shortlink
from ..notification import DecisionBranchBase, DecisionFactorBase, RenderNotification


@dataclass
class DecisionFactorFields:
    """Evaluation criteria for the content of notification."""

    is_member: bool | None = None
    for_actor: bool | None = None
    rtypes: Collection[str] = ()
    is_editor: bool | None = None
    is_promoter: bool | None = None
    is_usher: bool | None = None
    is_actor: bool | None = None
    is_self_granted: bool | None = None
    is_self_revoked: bool | None = None

    def is_match(
        self, membership: ProjectMembership, is_member: bool, for_actor: bool
    ) -> bool:
        """Test if this :class:`DecisionFactor` is a match."""
        return (
            (self.is_member is None or self.is_member is is_member)
            and (self.for_actor is None or self.for_actor is for_actor)
            and (not self.rtypes or membership.record_type_label.name in self.rtypes)
            and (self.is_editor is None or self.is_editor is membership.is_editor)
            and (self.is_promoter is None or self.is_promoter is membership.is_promoter)
            and (self.is_usher is None or self.is_usher is membership.is_usher)
            and (self.is_actor is None or (self.is_actor is membership.is_self_granted))
            and (
                self.is_self_granted is None
                or (self.is_self_granted is membership.is_self_granted)
            )
            and (
                self.is_self_revoked is None
                or (self.is_self_revoked is membership.is_self_revoked)
            )
        )


@dataclass
class DecisionFactor(DecisionFactorFields, DecisionFactorBase):
    """Decision factor for content of a project crew notification."""


@dataclass
class DecisionBranch(DecisionFactorFields, DecisionBranchBase):
    """Grouped decision factors for content of a project crew notification."""


# Sequential list of tests, evaluated in order
# pylint: disable=unexpected-keyword-arg
grant_amend_templates = DecisionBranch(
    factors=[
        DecisionBranch(
            rtypes=['invite'],
            factors=[
                DecisionBranch(
                    for_actor=False,
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be editor and promoter of"
                                " {project} by {actor}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be editor of {project} by"
                                " {actor}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be promoter of {project} by"
                                " {actor}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was invited to join the crew of {project} by"
                                " {actor}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=False,
                    is_member=True,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to be editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to be editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to be promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to join the crew of {project}"
                            ),
                            is_member=True,
                            rtypes=['invite'],
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You invited {user} to be editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("You invited {user} to be editor of {project}"),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You invited {user} to be promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You invited {user} to join the crew of {project}"
                            ),
                            rtypes=['invite'],
                            for_actor=True,
                        ),
                    ],
                ),
            ],
        ),
        DecisionBranch(
            rtypes=['accept'],
            factors=[
                DecisionBranch(
                    for_actor=False,
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{user} accepted an invite to be editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} accepted an invite to be editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} accepted an invite to be promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} accepted an invite to join the crew of"
                                " {project}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_member=True,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You accepted an invite to be editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You accepted an invite to be promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You accepted an invite to be editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You accepted an invite to join the crew of {project}"
                            ),
                        ),
                    ],
                ),
            ],
        ),
        DecisionBranch(
            rtypes=['direct_add'],
            factors=[
                DecisionBranch(
                    for_actor=False,
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{actor} joined {project} as editor and promoter"
                            ),
                            is_editor=True,
                            is_promoter=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} joined {project} as editor"),
                            is_editor=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} joined {project} as promoter"),
                            is_promoter=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} joined the crew of {project}"),
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was made editor and promoter of"
                                " {project} by {actor}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was made editor of {project} by {actor}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was made promoter of {project} by {actor}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} added {user} to the crew of {project}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=False,
                    is_member=True,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{actor} made you editor and promoter of {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} made you editor of {project}"),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} made you promoter of {project}"),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} added you to the crew of {project}"),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You made {user} editor and promoter of {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("You made {user} editor of {project}"),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__("You made {user} promoter of {project}"),
                            rtypes=['direct_add'],
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("You added {user} to the crew of {project}"),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_member=True,
                    factors=[
                        DecisionFactor(
                            template=__("You joined {project} as editor and promoter"),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("You joined {project} as editor"),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__("You joined {project} as promoter"),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("You joined the crew of {project}"),
                        ),
                    ],
                ),
            ],
        ),
        DecisionBranch(
            rtypes=['amend'],
            factors=[
                DecisionBranch(
                    for_actor=False,
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{user} changed their role to editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} changed their role to editor of {project}"
                            ),
                            is_editor=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} changed their role to promoter of {project}"
                            ),
                            is_promoter=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} changed their role to crew member of {project}"
                            ),
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}’s role was changed to editor and promoter of"
                                " {project} by {actor}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}’s role was changed to editor of {project} by"
                                " {actor}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}’s role was changed to promoter of {project} by"
                                " {actor}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}’s role was changed to crew member of {project}"
                                " by {actor}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=False,
                    is_member=True,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{actor} changed your role to editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} changed your role to editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} changed your role to promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} changed your role to crew member of {project}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You changed {user}’s role to editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}’s role to editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}’s role to promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}’s role to crew member of {project}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_member=True,
                    factors=[
                        DecisionFactor(
                            template=__("You are now editor and promoter of {project}"),
                            is_promoter=True,
                            is_editor=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__("You changed your role to editor of {project}"),
                            is_editor=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed your role to promoter of {project}"
                            ),
                            is_promoter=True,
                            is_self_granted=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed your role to crew member of {project}"
                            ),
                            rtypes=['amend'],
                            is_self_granted=True,
                        ),
                    ],
                ),
            ],
        ),
    ],
)

# pylint: disable=unexpected-keyword-arg
revoke_templates = DecisionBranch(
    factors=[
        DecisionBranch(
            for_actor=False,
            is_member=False,
            factors=[
                DecisionFactor(
                    template=__("{user} resigned as editor and promoter of {project}"),
                    is_editor=True,
                    is_promoter=True,
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__("{user} resigned as editor of {project}"),
                    is_editor=True,
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__("{user} resigned as promoter of {project}"),
                    is_promoter=True,
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__("{user} resigned from the crew of {project}"),
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__(
                        "{user} was removed as editor and promoter of {project} by"
                        " {actor}"
                    ),
                    is_promoter=True,
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__("{user} was removed as editor of {project} by {actor}"),
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__(
                        "{user} was removed as promoter of {project} by {actor}"
                    ),
                    is_promoter=True,
                ),
                DecisionFactor(
                    template=__("{user} was removed as crew of {project} by {actor}"),
                ),
            ],
        ),
        DecisionBranch(
            for_actor=False,
            is_member=True,
            factors=[
                DecisionFactor(
                    template=__(
                        "{actor} removed you as editor and promoter of {project}"
                    ),
                    is_promoter=True,
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__("{actor} removed you as editor of {project}"),
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__("{actor} removed you as promoter of {project}"),
                    is_promoter=True,
                ),
                DecisionFactor(
                    template=__("{actor} removed you from the crew of {project}"),
                ),
            ],
        ),
        DecisionBranch(
            for_actor=True,
            factors=[
                DecisionFactor(
                    template=__("You resigned as editor and promoter of {project}"),
                    is_editor=True,
                    is_promoter=True,
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__("You resigned as editor of {project}"),
                    is_editor=True,
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__("You resigned as promoter of {project}"),
                    is_promoter=True,
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__("You resigned from the crew of {project}"),
                    is_self_revoked=True,
                ),
                DecisionFactor(
                    template=__(
                        "You removed {user} as editor and promoter of {project}"
                    ),
                    is_editor=True,
                    is_promoter=True,
                ),
                DecisionFactor(
                    template=__("You removed {user} as editor of {project}"),
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__("You removed {user} as promoter of {project}"),
                    is_promoter=True,
                ),
                DecisionFactor(
                    template=__("You removed {user} from the crew of {project}"),
                ),
            ],
        ),
    ]
)


class RenderShared:
    emoji_prefix = "🔑 "
    reason = __("You are receiving this because you are a crew member of this project")

    project: Project
    membership: ProjectMembership
    notification: NotificationType
    notification_recipient: NotificationRecipient
    #: Subclasses must specify a base template picker
    template_picker: DecisionBranch

    tracking_tags: ClassVar[Callable[..., dict[str, str]]]

    def activity_template(self, membership: ProjectMembership | None = None) -> str:
        """
        Return a Python string template with an appropriate message.

        Accepts an optional membership object for use in rollups.
        """
        if membership is None:
            membership = self.membership
        membership_actor = self.membership_actor(membership)
        match = self.template_picker.match(
            membership,
            is_member=self.notification_recipient.recipient == membership.member,
            for_actor=self.notification_recipient.recipient == membership_actor,
        )
        if match is not None:
            return match.template
        raise ValueError("No suitable template found for membership record")

    def membership_actor(
        self, membership: ProjectMembership | None = None
    ) -> Account | None:
        """Actor who granted or revoked, for the template."""
        raise NotImplementedError("Subclasses must implement `membership_actor`")

    @property
    def actor(self) -> Account:
        """
        We're interested in who has the membership, not who granted/revoked it.

        However, if the notification is being rendered for the member in the
        membership, the original actor must be attributed.
        """
        if (
            self.notification_recipient.recipient == self.membership.member
            and self.notification.created_by is not None
        ):
            return self.notification.created_by
        return self.membership.member

    def activity_html(self, membership: ProjectMembership | None = None) -> str:
        """Return HTML rendering of :meth:`activity_template`."""
        if membership is None:
            membership = self.membership
        actor = self.membership_actor(membership)
        return Markup(self.activity_template(membership)).format(
            user=Markup(
                f'<a href="{escape(membership.member.absolute_url)}">'
                f'{escape(membership.member.pickername)}</a>'
            ),
            project=Markup(
                f'<a href="{escape(self.project.absolute_url)}">'
                f'{escape(self.project.joined_title)}</a>'
            ),
            actor=(
                Markup(
                    f'<a href="{escape(actor.absolute_url)}">'
                    f'{escape(actor.pickername)}</a>'
                )
            )
            if actor
            else _("(unknown)"),
        )

    def email_subject(self) -> str:
        """Subject line for email."""
        actor = self.membership_actor()
        return self.emoji_prefix + self.activity_template().format(
            user=self.membership.member.pickername,
            project=self.project.joined_title,
            actor=(actor.pickername if actor is not None else _("(unknown)")),
        )

    def sms(self) -> OneLineTemplate:
        """SMS notification."""
        actor = self.membership_actor()
        return OneLineTemplate(
            text1=self.activity_template().format(
                user=self.membership.member.pickername,
                project=self.project.joined_title,
                actor=(actor.pickername if actor is not None else _("(unknown)")),
            ),
            url=shortlink(
                self.project.url_for(
                    'crew', _external=True, **self.tracking_tags('sms')
                ),
                shorter=True,
            ),
        )


@ProjectCrewMembershipNotification.renderer
class RenderProjectCrewMembershipNotification(RenderShared, RenderNotification):
    """Render a notification for project crew invite/add/amend."""

    aliases = {'document': 'project', 'fragment': 'membership'}
    hero_image = 'img/email/chars-v1/access-granted.png'
    email_heading = __("Crew membership granted!")
    fragments_order_by = [ProjectMembership.granted_at.desc()]
    template_picker = grant_amend_templates

    def membership_actor(self, membership: ProjectMembership | None = None) -> Account:
        """Actual actor who granted (or edited) the membership, for the template."""
        return (membership or self.membership).granted_by

    def web(self):
        return render_template(
            'notifications/project_crew_membership_granted_web.html.jinja2', view=self
        )

    def email_content(self):
        return render_template(
            'notifications/project_crew_membership_granted_email.html.jinja2', view=self
        )


@ProjectCrewMembershipRevokedNotification.renderer
class RenderProjectCrewMembershipRevokedNotification(RenderShared, RenderNotification):
    """Render a notification for project crew revocation."""

    aliases = {'document': 'project', 'fragment': 'membership'}
    hero_image = 'img/email/chars-v1/access-revoked.png'
    email_heading = __("Crew membership revoked")
    template_picker = revoke_templates

    def membership_actor(
        self, membership: ProjectMembership | None = None
    ) -> Account | None:
        """Actual actor who revoked the membership, for the template."""
        return (membership or self.membership).revoked_by

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
