"""Organization admin and project crew membership notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Optional, cast

from flask import render_template
from markupsafe import Markup, escape

from baseframe import _, __

from ...models import (
    Account,
    AccountAdminMembership,
    NotificationType,
    OrganizationAdminMembershipNotification,
    OrganizationAdminMembershipRevokedNotification,
    UserNotification,
)
from ...transports.sms import MessageTemplate
from ..notification import DecisionBranchBase, DecisionFactorBase, RenderNotification


@dataclass
class DecisionFactorFields:
    """Evaluation criteria for the content of notification (for grants/edits only)."""

    is_member: Optional[bool] = None
    for_actor: Optional[bool] = None
    rtypes: Collection[str] = ()
    is_owner: Optional[bool] = None
    is_actor: Optional[bool] = None

    def is_match(
        self,
        membership: AccountAdminMembership,
        is_member: bool,
        for_actor: bool,
    ) -> bool:
        """Test if this :class:`DecisionFactor` is a match."""
        return (
            (self.is_member is None or self.is_member is is_member)
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
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be owner of {organization} by"
                                " {actor}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was invited to be admin of {organization} by"
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
                    is_member=False,
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
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{user} was made owner of {organization} by {actor}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user} was made admin of {organization} by {actor}"
                            ),
                        ),
                    ],
                ),
                DecisionBranch(
                    for_actor=False,
                    is_member=True,
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
                    is_member=False,
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
                    is_member=False,
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
                    is_member=True,
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
                    is_member=True,
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
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "{user}’s role was changed to owner of {organization}"
                                " by {actor}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "{user}’s role was changed to admin of {organization}"
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
                    is_member=False,
                    factors=[
                        DecisionFactor(
                            template=__(
                                "You changed {user}’s role to owner of {organization}"
                            ),
                            is_owner=True,
                        ),
                        DecisionFactor(
                            template=__(
                                "You changed {user}’s role to admin of {organization}"
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
            is_member=False,
            factors=[
                DecisionFactor(
                    template=__(
                        "{user} was removed as owner of {organization} by {actor}"
                    ),
                    is_owner=True,
                ),
                DecisionFactor(
                    template=__(
                        "{user} was removed as admin of {organization} by {actor}"
                    ),
                ),
            ],
        ),
        DecisionBranch(
            for_actor=False,
            is_member=True,
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
            is_member=False,
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
    emoji_prefix = "🔑 "
    reason = __("You are receiving this because you are an admin of this organization")

    organization: Account
    membership: AccountAdminMembership
    notification: NotificationType
    user_notification: UserNotification
    template_picker: DecisionBranch

    def activity_template(
        self, membership: Optional[AccountAdminMembership] = None
    ) -> str:
        """Return a Python string template with an appropriate message."""
        if membership is None:
            membership = self.membership
        membership_actor = self.membership_actor(membership)
        match = self.template_picker.match(
            membership,
            is_member=self.user_notification.user == membership.member,
            for_actor=self.user_notification.user == membership_actor,
        )
        if match is not None:
            return match.template
        raise ValueError("No suitable template found for membership record")

    def membership_actor(
        self, membership: Optional[AccountAdminMembership] = None
    ) -> Optional[Account]:
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
            self.user_notification.user == self.membership.member
            and self.notification.user is not None
        ):
            return self.notification.user
        return self.membership.member

    def activity_html(self, membership: Optional[AccountAdminMembership] = None) -> str:
        """Return HTML rendering of :meth:`activity_template`."""
        if membership is None:
            membership = self.membership
        actor = self.membership_actor(membership)
        return Markup(self.activity_template(membership)).format(
            user=Markup(
                f'<a href="{escape(membership.member.profile_url)}">'
                f'{escape(membership.member.pickername)}</a>'
            )
            if membership.member.profile_url
            else escape(membership.member.pickername),
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
            user=self.membership.member.pickername,
            organization=self.organization.pickername,
            actor=(actor.pickername if actor is not None else _("(unknown)")),
        )

    def sms(self) -> MessageTemplate:
        """SMS notification."""
        actor = self.membership_actor()
        return MessageTemplate(
            message=self.activity_template().format(
                user=self.membership.member.pickername,
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

    fragments_order_by = [AccountAdminMembership.granted_at.desc()]

    def membership_actor(
        self, membership: Optional[AccountAdminMembership] = None
    ) -> Optional[Account]:
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

    fragments_order_by = [AccountAdminMembership.revoked_at.desc()]

    def membership_actor(
        self, membership: Optional[AccountAdminMembership] = None
    ) -> Optional[Account]:
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
