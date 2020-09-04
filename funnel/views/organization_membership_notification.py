"""Organization admin and project crew membership notifications."""

from typing import List, NamedTuple, Optional

from flask import Markup, escape, render_template

from baseframe import _, __

from ..models import (
    MEMBERSHIP_RECORD_TYPE,
    OrganizationAdminMembershipNotification,
    OrganizationAdminMembershipRevokedNotification,
    OrganizationMembership,
)
from .notification import RenderNotification


class DecisionFactor(NamedTuple):
    """Evaluation criteria for the content of notification"""

    template: str
    is_subject: bool = False
    rtypes: List[str] = []
    is_owner: Optional[bool] = None
    is_actor: Optional[bool] = None

    def match(self, is_subject, record_type, membership):
        return (
            (self.is_subject is is_subject)
            and (not self.rtypes or record_type in self.rtypes)
            and (self.is_owner is None or self.is_owner is membership.is_owner)
            and (
                self.is_actor is None
                or (self.is_actor is bool(membership.user == membership.granted_by))
            )
        )


# Sequential list of tests, evaluated in order
decision_factors = [
    # --- Subject has been invited by someone (self appointment not possible)
    DecisionFactor(
        template=__("You have been invited as an owner of {organization} by {actor}"),
        is_subject=True,
        rtypes=['invite'],
        is_owner=True,
    ),
    DecisionFactor(
        template=__("You have been invited as an admin of {organization} by {actor}"),
        is_subject=True,
        rtypes=['invite'],
        is_owner=False,
    ),
    # --- Subject has accepted an invite (this should NOT trigger a notification)
    DecisionFactor(
        template=__("You are now an owner of {organization}"),
        is_subject=True,
        rtypes=['accept'],
        is_owner=True,
    ),
    DecisionFactor(
        template=__("You are now an admin of {organization}"),
        is_subject=True,
        rtypes=['accept'],
        is_owner=False,
    ),
    # --- Subject has amended their own role (this should NOT trigger a notification)
    DecisionFactor(  # This should never happen
        template=__("You have changed your role to owner of {organization}"),
        is_subject=True,
        rtypes=['amend'],
        is_owner=True,
        is_actor=True,
    ),
    DecisionFactor(  # Subject demoted themselves
        template=__("You have changed your role to an admin of {organization}"),
        is_subject=True,
        rtypes=['amend'],
        is_owner=False,
        is_actor=True,
    ),
    # --- Subject has been appointed (add or amend) by someone else
    DecisionFactor(
        template=__("You were added as an owner of {organization} by {actor}"),
        is_subject=True,
        rtypes=['direct_add'],
        is_owner=True,
        is_actor=False,
    ),
    DecisionFactor(
        template=__("You were added as an admin of {organization} by {actor}"),
        is_subject=True,
        rtypes=['direct_add'],
        is_owner=False,
        is_actor=False,
    ),
    DecisionFactor(
        template=__("Your role was changed to owner of {organization} by {actor}"),
        is_subject=True,
        rtypes=['amend'],
        is_owner=True,
        is_actor=False,
    ),
    DecisionFactor(
        template=__("Your role was changed to admin of {organization} by {actor}"),
        is_subject=True,
        rtypes=['amend'],
        is_owner=False,
        is_actor=False,
    ),
    # --- Notifications to other admins of organization (except actor) -----------------
    # --- User was invited
    DecisionFactor(
        template=__("{user} was invited to be an owner of {organization} by {actor}"),
        rtypes=['invite'],
        is_owner=True,
    ),
    DecisionFactor(
        template=__("{user} was invited to be an admin of {organization} by {actor}"),
        rtypes=['invite'],
        is_owner=False,
    ),
    # --- User accepted
    DecisionFactor(
        template=__("{user} is now an owner of {organization}"),
        rtypes=['accept'],
        is_owner=True,
    ),
    DecisionFactor(
        template=__("{user} is now an admin of {organization}"),
        rtypes=['accept'],
        is_owner=False,
    ),
    # --- User changed their own role
    DecisionFactor(  # This should not happen. User can't upgrade their own role
        template=__("{user} changed their role to owner of {organization}"),
        rtypes=['amend'],
        is_owner=True,
        is_actor=True,
    ),
    DecisionFactor(
        template=__("{user} changed their role from owner to admin of {organization}"),
        rtypes=['amend'],
        is_owner=False,
        is_actor=True,
    ),
    # --- User was added
    DecisionFactor(
        template=__("{user} was made an owner of {organization} by {actor}"),
        rtypes=['direct_add', 'amend'],
        is_owner=True,
    ),
    DecisionFactor(
        template=__("{user} was made an admin of {organization} by {actor}"),
        rtypes=['direct_add', 'amend'],
        is_owner=False,
    ),
]


class RenderShared:
    emoji_prefix = "🔑 "

    @property
    def actor(self):
        """We're interested in who has the membership, not who granted/revoked it."""
        return self.membership.user

    @property
    def record_type(self):
        """Helper method for templates to analyse membership record type."""
        # There are four record types: invite, accept, direct_add, amend
        return MEMBERSHIP_RECORD_TYPE[self.membership.record_type].name

    def activity_html(self, membership=None):
        if not membership:
            membership = self.membership
        return Markup(self.activity_template(membership)).format(
            user=Markup(
                '<a href="{url}">{name}</a>'.format(
                    url=escape(membership.user.profile_url),
                    name=escape(membership.user.pickername),
                )
            )
            if membership.user.profile_url
            else escape(membership.user.pickername),
            organization=Markup(
                '<a href="{url}">{title}</a>'.format(
                    url=escape(self.organization.profile_url),
                    title=escape(self.organization.pickername),
                )
            ),
            actor=Markup(
                '<a href="{url}">{name}</a>'.format(
                    url=escape(membership.granted_by.profile_url),
                    name=escape(membership.granted_by.pickername),
                )
            )
            if membership.granted_by.profile_url
            else escape(membership.granted_by.pickername),
        )

    def email_subject(self):
        return self.emoji_prefix + (f"{self.activity_template()}").format(
            user=self.membership.user.pickername,
            organization=self.organization.pickername,
            actor=self.membership.granted_by.pickername,
        )

    def sms(self):
        return (f"{self.activity_template()}").format(
            user=self.membership.user.pickername,
            organization=self.organization.pickername,
            actor=self.membership.granted_by.pickername,
        )


@OrganizationAdminMembershipNotification.renderer
class RenderOrganizationAdminMembershipNotification(RenderShared, RenderNotification):
    """Notify organization admins of new admins and role changes."""

    aliases = {'document': 'organization', 'fragment': 'membership'}
    reason = __("You are receiving this because you are an admin of this organization.")

    def activity_template(self, membership=None):
        """
        Returns a returns a Python string template with an appropriate message.

        Accepts an optional membership object for use in rollups.
        """
        if not membership:
            membership = self.membership
        for df in decision_factors:
            if df.match(
                # LHS = user object, RHS = role proxy, so compare uuid
                self.user_notification.user.uuid == membership.user.uuid,
                self.record_type,
                membership,
            ):
                return df.template

    def web(self):
        memberships = [
            _m.access_for(actor=self.user_notification.user)
            for _m in self.user_notification.rolledup_fragments()
            .order_by(OrganizationMembership.granted_at.desc())
            .all()
        ]
        return render_template(
            'notifications/organization_membership_granted_web.html.jinja2',
            view=self,
            memberships=memberships,
            is_rollup=len(memberships) > 1,  # Required by layout template
        )

    def email_content(self):
        return render_template(
            'notifications/organization_membership_granted_email.html.jinja2', view=self
        )


@OrganizationAdminMembershipRevokedNotification.renderer
class RenderOrganizationAdminMembershipRevokedNotification(
    RenderShared, RenderNotification
):
    """Notify organization admins of removed admins."""

    aliases = {'document': 'organization', 'fragment': 'membership'}
    reason = __(
        "You are receiving this because you were an admin of this organization."
    )

    def activity_template(self, membership=None):
        """Return a single line summary of changes."""
        if not membership:
            membership = self.membership
        # LHS = user object, RHS = role proxy, so compare uuid
        if self.user_notification.user.uuid == membership.user.uuid:
            if membership.user == membership.revoked_by:
                return _("You removed yourself as an admin of {organization}")
            return _("You were removed as an admin of {organization} by {actor}")
        return _("{user} was removed as an admin of {organization} by {actor}")

    def web(self):
        memberships = [
            _m.access_for(actor=self.user_notification.user)
            for _m in self.user_notification.rolledup_fragments()
            .order_by(OrganizationMembership.revoked_at.desc())
            .all()
        ]
        return render_template(
            'notifications/organization_membership_revoked_web.html.jinja2',
            view=self,
            memberships=memberships,
            is_rollup=len(memberships) > 1,  # Required by layout template
        )

    def email_content(self):
        return render_template(
            'notifications/organization_membership_revoked_email.html.jinja2', view=self
        )
