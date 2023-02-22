"""Project crew notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, ClassVar, Collection, Dict, Optional

from flask import Markup, escape, render_template

from baseframe import _, __

from ...models import (
    Notification,
    Project,
    ProjectCrewMembership,
    ProjectCrewMembershipNotification,
    ProjectCrewMembershipRevokedNotification,
    User,
    UserNotification,
)
from ...transports.sms import OneLineTemplate
from ..helpers import shortlink
from ..notification import DecisionBranchBase, DecisionFactorBase, RenderNotification


@dataclass
class DecisionFactorFields:
    """Evaluation criteria for the content of notification."""

    is_subject: Optional[bool] = None
    for_actor: Optional[bool] = None
    rtypes: Collection[str] = ()
    is_editor: Optional[bool] = None
    is_promoter: Optional[bool] = None
    is_usher: Optional[bool] = None
    is_actor: Optional[bool] = None
    is_self_granted: Optional[bool] = None
    is_self_revoked: Optional[bool] = None

    def is_match(
        self, membership: ProjectCrewMembership, is_subject: bool, for_actor: bool
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
                    is_subject=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be an editor and promoter of"
                                " {project} by {actor}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be an editor of {project} by"
                                " {actor}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be a promoter of {project} by"
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
                    is_subject=True,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to be an editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to be an editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to be a promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to join the crew of {project}"
                            ),
                            is_subject=True,
                            rtypes=['invite'],
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_subject=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You invited {user} to be an editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You invited {user} to be an editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You invited {user} to be a promoter of {project}"
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
                    is_subject=False,
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
                    is_subject=True,
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
                    is_subject=False,
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
                    is_subject=True,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{actor} made you an editor and promoter of {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} made you an editor of {project}"),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} made you a promoter of {project}"),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} added you to the crew of {project}"),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_subject=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You made {user} an editor and promoter of {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__("You made {user} an editor of {project}"),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__("You made {user} a promoter of {project}"),
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
                    is_subject=True,
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
                    is_subject=False,
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
                                "{user}'s role to editor and promoter of {project} was"
                                " changed by {actor}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}'s role to editor of {project} was changed by"
                                " {actor}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}'s role to promoter of {project} was changed by"
                                " {actor}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}'s role to crew member of {project} was changed"
                                " by {actor}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=False,
                    is_subject=True,
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
                    is_subject=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You changed {user}'s role to editor and promoter of"
                                " {project}"
                            ),
                            is_editor=True,
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}'s role to editor of {project}"
                            ),
                            is_editor=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}'s role to promoter of {project}"
                            ),
                            is_promoter=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}'s role to crew member of {project}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_subject=True,
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
            is_subject=False,
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
            is_subject=True,
            factors=[
                DecisionFactor(
                    template=__(
                        "{actor} removed you from editor and promoter of {project}"
                    ),
                    is_promoter=True,
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__("{actor} removed you from editor of {project}"),
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__("{actor} removed you from promoter of {project}"),
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
                        "You removed {user} from editor and promoter of {project}"
                    ),
                    is_editor=True,
                    is_promoter=True,
                ),
                DecisionFactor(
                    template=__("You removed {user} from editor of {project}"),
                    is_editor=True,
                ),
                DecisionFactor(
                    template=__("You removed {user} from promoter of {project}"),
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
    membership: ProjectCrewMembership
    notification: Notification
    user_notification: UserNotification
    #: Subclasses must specify a base template picker
    template_picker: DecisionBranch

    tracking_tags: ClassVar[Callable[..., Dict[str, str]]]

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
        match = self.template_picker.match(
            membership,
            is_subject=self.user_notification.user.uuid == membership_user_uuid,
            for_actor=self.user_notification.user.uuid == membership_actor_uuid,
        )
        if match is not None:
            return match.template
        raise ValueError("No suitable template found for membership record")

    def membership_actor(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> Optional[User]:
        """Actor who granted or revoked, for the template."""
        raise NotImplementedError("Subclasses must implement `membership_actor`")

    @property
    def actor(self) -> User:
        """
        We're interested in who has the membership, not who granted/revoked it.

        However, if the notification is being rendered for the person who is the subject
        of the membership, the original actor must be attributed.
        """
        if (
            self.user_notification.user.uuid == self.membership.user.uuid
            and self.notification.user is not None
        ):
            return self.notification.user
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

    def sms(self) -> OneLineTemplate:
        """SMS notification."""
        actor = self.membership_actor()
        return OneLineTemplate(
            text1=self.activity_template().format(
                user=self.membership.user.pickername,
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
    fragments_order_by = [ProjectCrewMembership.granted_at.desc()]
    template_picker = grant_amend_templates

    def membership_actor(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> User:
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
    template_picker = revoke_templates

    def membership_actor(
        self, membership: Optional[ProjectCrewMembership] = None
    ) -> Optional[User]:
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
