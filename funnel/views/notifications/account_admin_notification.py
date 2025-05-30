"""Organization admin and project crew membership notifications."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import cast

from flask import render_template
from markupsafe import Markup
from werkzeug.utils import cached_property

from baseframe import _, __

from ...models import (
    Account,
    AccountAdminNotification,
    AccountAdminRevokedNotification,
    AccountMembership,
    MembershipRecordTypeEnum,
    Notification,
    NotificationRecipient,
    sa,
)
from ..notification import DecisionBranchBase, DecisionFactorBase, RenderNotification


@dataclass
class DecisionFactorFields:
    """Evaluation criteria for the content of notification (for grants/edits only)."""

    is_member: bool | None = None
    for_actor: bool | None = None
    rtypes: Collection[MembershipRecordTypeEnum] = ()
    is_owner: bool | None = None
    is_actor: bool | None = None

    def is_match(
        self,
        membership: AccountMembership,
        is_member: bool,
        for_actor: bool,
    ) -> bool:
        """Test if this :class:`DecisionFactor` is a match."""
        return (
            (self.is_member is None or self.is_member is is_member)
            and (self.for_actor is None or self.for_actor is for_actor)
            and (not self.rtypes or membership.record_type_enum in self.rtypes)
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
            rtypes=[MembershipRecordTypeEnum.INVITE],
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
            rtypes=[MembershipRecordTypeEnum.DIRECT_ADD],
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
            rtypes=[MembershipRecordTypeEnum.ACCEPT],
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
            rtypes=[MembershipRecordTypeEnum.AMEND],
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

    account: Account
    membership: AccountMembership
    notification: Notification
    notification_recipient: NotificationRecipient
    template_picker: DecisionBranch

    def activity_template(self, membership: AccountMembership | None = None) -> str:
        """Return a Python string template with an appropriate message."""
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
        self, membership: AccountMembership | None = None
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

    def activity_html(self, membership: AccountMembership | None = None) -> str:
        """Return HTML rendering of :meth:`activity_template`."""
        if membership is None:
            membership = self.membership
        actor = self.membership_actor(membership)
        return Markup(self.activity_template(membership)).format(  # noqa: S704
            user=Markup('<a href="{url}">{name}</a>').format(
                url=membership.member.absolute_url, name=membership.member.pickername
            ),
            organization=Markup('<a href="{url}">{name}</a>').format(
                url=cast(str, self.account.absolute_url), name=self.account.pickername
            ),
            actor=(
                Markup('<a href="{url}">{name}</a>').format(
                    url=actor.absolute_url, name=actor.pickername
                )
                if actor
                else _("(unknown)")
            ),
        )

    def email_subject(self) -> str:
        """Subject line for email."""
        actor = self.membership_actor()
        return self.emoji_prefix + self.activity_template().format(
            user=self.membership.member.pickername,
            organization=self.account.pickername,
            actor=(actor.pickername if actor is not None else _("(unknown)")),
        )


@AccountAdminNotification.renderer
class RenderAccountAdminNotification(RenderShared, RenderNotification):
    """Notify account admins of new admins and role changes."""

    aliases = {'document': 'account', 'fragment': 'membership'}
    reason = __("You are receiving this because you are an admin of this organization")
    hero_image = 'img/email/chars-v1/access-granted.png'
    email_heading = __("Membership granted!")
    template_picker = grant_amend_templates

    @cached_property
    def fragments_order_by(self) -> list[sa.UnaryExpression]:
        return [AccountMembership.granted_at.desc()]

    def membership_actor(
        self, membership: AccountMembership | None = None
    ) -> Account | None:
        """Actual actor who granted (or edited) the membership, for the template."""
        return (membership or self.membership).granted_by

    def web(self) -> str:
        """Render for web."""
        return render_template(
            'notifications/account_admin_granted_web.html.jinja2', view=self
        )

    def email_content(self) -> str:
        """Render email content."""
        return render_template(
            'notifications/account_admin_granted_email.html.jinja2', view=self
        )


@AccountAdminRevokedNotification.renderer
class RenderAccountAdminRevokedNotification(RenderShared, RenderNotification):
    """Notify account admins of removed admins."""

    aliases = {'document': 'account', 'fragment': 'membership'}
    reason = __("You are receiving this because you were an admin of this organization")
    hero_image = 'img/email/chars-v1/access-revoked.png'
    email_heading = __("Membership revoked")
    template_picker = revoke_templates

    @cached_property
    def fragments_order_by(self) -> list[sa.UnaryExpression]:
        return [AccountMembership.revoked_at.desc()]

    def membership_actor(
        self, membership: AccountMembership | None = None
    ) -> Account | None:
        """Actual actor who revoked the membership, for the template."""
        return (membership or self.membership).revoked_by

    def web(self) -> str:
        """Render for web."""
        return render_template(
            'notifications/account_admin_revoked_web.html.jinja2', view=self
        )

    def email_content(self) -> str:
        """Render email content."""
        return render_template(
            'notifications/account_admin_revoked_email.html.jinja2', view=self
        )
