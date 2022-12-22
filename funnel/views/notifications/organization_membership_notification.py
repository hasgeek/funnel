"""Organization admin and project crew membership notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Optional, cast

from flask import Markup, escape, render_template

from baseframe import _, __

from ...models import (
    Organization,
    OrganizationAdminMembershipNotification,
    OrganizationAdminMembershipRevokedNotification,
    OrganizationMembership,
    User,
    UserNotification,
)
from ...transports.sms import MessageTemplate
from ..notification import DecisionBranchBase, DecisionFactorBase, RenderNotification


@dataclass
class DecisionFactorFields:
    """Evaluation criteria for the content of notification (for grants/edits only)."""

    is_subject: Optional[bool] = None
    for_actor: Optional[bool] = None
    rtypes: Collection[str] = ()
    is_owner: Optional[bool] = None
    is_actor: Optional[bool] = None

    def is_match(
        self,
        membership: OrganizationMembership,
        is_subject: bool,
        for_actor: bool,
    ) -> bool:
        """Test if this :class:`DecisionFactor` is a match."""
        return (
            (self.is_subject is None or self.is_subject is is_subject)
            and (self.for_actor is None or self.for_actor is for_actor)
            and (not self.rtypes or membership.record_type_label.name in self.rtypes)
            and (self.is_owner is None or self.is_owner is membership.is_owner)
            and (self.is_actor is None or (self.is_actor is membership.is_self_granted))
        )


@dataclass
class DecisionFactor(DecisionFactorFields, DecisionFactorBase):
    """Decision factor for content of an org membership notification."""


@dataclass
class DecisionBranch(DecisionFactorFields, DecisionBranchBase):
    """Grouped decision factors for content of an org membership notification."""


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
                                "{actor} invited {user} to be owner of {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited {user} to be admin of {organization}"
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
                                "{actor} invited you to be owner of {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} invited you to be admin of {organization}"
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
                                "You invited {user} to be owner of {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You invited {user} to be admin of {organization}"
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
                            template=__("{actor} made {user} owner of {organization}"),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} made {user} admin of {organization}"),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=False,
                    is_subject=True,
                    factors=[
                        DecisionFactor(
                            template=__("{actor} made you owner of {organization}"),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__("{actor} made you admin of {organization}"),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=True,
                    is_subject=False,
                    factors=[
                        DecisionFactor(
                            template=__("You made {user} owner of {organization}"),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__("You made {user} admin of {organization}"),
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
                                "{user} accepted an invite to be owner of"
                                " {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} accepted an invite to be admin of"
                                " {organization}"
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
                                "{user} accepted an invite to be owner of"
                                " {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} accepted an invite to be admin of"
                                " {organization}"
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
                                "You accepted an invite to be owner of {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You accepted an invite to be admin of {organization}"
                            ),
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
                                "{actor} changed {user}'s role to owner of"
                                " {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} changed {user}'s role to admin of"
                                " {organization}"
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
                                "{actor} changed your role to owner of {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{actor} changed your role to admin of {organization}"
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
                                "You changed {user}'s role to owner of {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}'s role to admin of {organization}"
                            ),
                        ),
                    ],
                ),
            ],
        ),
    ]
)


revoke_templates = DecisionBranch(
    factors=[
        DecisionBranch(
            for_actor=False,
            is_subject=False,
            factors=[
                DecisionFactor(
                    template=__("{actor} removed {user} from owner of {organization}"),
                    is_owner=True,
                ),
                DecisionFactor(
                    template=__("{actor} removed {user} from admin of {organization}"),
                ),
            ],
        ),
        DecisionBranch(
            for_actor=False,
            is_subject=True,
            factors=[
                DecisionFactor(
                    template=__("{actor} removed you from owner of {organization}"),
                    is_owner=True,
                ),
                DecisionFactor(
                    template=__("{actor} removed you from admin of {organization}"),
                ),
            ],
        ),
        DecisionBranch(
            for_actor=True,
            is_subject=False,
            factors=[
                DecisionFactor(
                    template=__("You removed {user} from owner of {organization}"),
                    is_owner=True,
                ),
                DecisionFactor(
                    template=__("You removed {user} from admin of {organization}"),
                ),
            ],
        ),
    ]
)


class RenderShared:
    organization: Organization
    membership: OrganizationMembership
    emoji_prefix = "🔑 "
    user_notification: UserNotification
    template_picker: DecisionBranch

    def activity_template(
        self, membership: Optional[OrganizationMembership] = None
    ) -> str:
        """Return a Python string template with an appropriate message."""
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
        self, membership: Optional[OrganizationMembership] = None
    ) -> Optional[User]:
        """Actor who granted or revoked, for the template."""
        raise NotImplementedError("Subclasses must implement `membership_actor`")

    @property
    def actor(self) -> User:
        """We're interested in who has the membership, not who granted/revoked it."""
        return self.membership.user

    def activity_html(self, membership: Optional[OrganizationMembership] = None) -> str:
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
            organization=Markup(
                f'<a href="{escape(cast(str, self.organization.profile_url))}">'
                f'{escape(self.organization.pickername)}</a>'
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
            organization=self.organization.pickername,
            actor=(actor.pickername if actor is not None else _("(unknown)")),
        )

    def sms(self) -> MessageTemplate:
        """SMS notification."""
        actor = self.membership_actor()
        return MessageTemplate(
            message=self.activity_template().format(
                user=self.membership.user.pickername,
                organization=self.organization.pickername,
                actor=(actor.pickername if actor is not None else _("(unknown)")),
            )
        )


@OrganizationAdminMembershipNotification.renderer
class RenderOrganizationAdminMembershipNotification(RenderShared, RenderNotification):
    """Notify organization admins of new admins and role changes."""

    aliases = {'document': 'organization', 'fragment': 'membership'}
    reason = __("You are receiving this because you are an admin of this organization")
    template_picker = grant_amend_templates

    fragments_order_by = [OrganizationMembership.granted_at.desc()]

    def membership_actor(
        self, membership: Optional[OrganizationMembership] = None
    ) -> Optional[User]:
        """Actual actor who granted (or edited) the membership, for the template."""
        return (membership or self.membership).granted_by

    def web(self) -> str:
        """Render for web."""
        return render_template(
            'notifications/organization_membership_granted_web.html.jinja2', view=self
        )

    def email_content(self) -> str:
        """Render email content."""
        return render_template(
            'notifications/organization_membership_granted_email.html.jinja2', view=self
        )


@OrganizationAdminMembershipRevokedNotification.renderer
class RenderOrganizationAdminMembershipRevokedNotification(
    RenderShared, RenderNotification
):
    """Notify organization admins of removed admins."""

    aliases = {'document': 'organization', 'fragment': 'membership'}
    reason = __("You are receiving this because you were an admin of this organization")
    template_picker = revoke_templates

    fragments_order_by = [OrganizationMembership.revoked_at.desc()]

    def membership_actor(
        self, membership: Optional[OrganizationMembership] = None
    ) -> Optional[User]:
        """Actual actor who revoked the membership, for the template."""
        return (membership or self.membership).revoked_by

    def web(self) -> str:
        """Render for web."""
        return render_template(
            'notifications/organization_membership_revoked_web.html.jinja2', view=self
        )

    def email_content(self) -> str:
        """Render email content."""
        return render_template(
            'notifications/organization_membership_revoked_email.html.jinja2', view=self
        )
