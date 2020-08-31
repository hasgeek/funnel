"""Organization admin and project crew membership notifications."""

from flask import render_template

from baseframe import _, __

from ..models import (
    MEMBERSHIP_RECORD_TYPE,
    OrganizationAdminMembershipNotification,
    OrganizationAdminMembershipRevokedNotification,
    OrganizationMembership,
)
from .notification import RenderNotification


@OrganizationAdminMembershipNotification.renderer
class RenderOrganizationAdminMembershipNotification(RenderNotification):
    """Notify organization admins of new admins and role changes."""

    aliases = {'document': 'organization', 'fragment': 'membership'}
    reason = __("You are receiving this because you are an admin of this organization.")

    @property
    def record_type(self):
        """Helper method for templates to analyse membership record type."""
        # There are four record types: invite, accept, direct_add, amend
        return MEMBERSHIP_RECORD_TYPE[self.membership.record_type].name

    def activity_fact(self):
        """Return a single line summary of changes."""
        # --- Notification is being sent to the subject of the membership
        if self.user_notification.role == 'subject':
            if self.membership.is_owner:
                fact = _("You are now an owner of {organization}.").format(
                    organization=self.organization.pickername
                )
            else:
                fact = _("You are now an admin of {organization}.").format(
                    organization=self.organization.pickername
                )
            if self.membership.granted_by != self.membership.user:
                # Actor will also be the subject for `accept` type, and for `amend`
                # when they demote themselves. In all other cases, actor will be someone
                # else.
                if self.record_type == 'direct_add':
                    fact += ' ' + _("Added by {actor}.").format(
                        actor=self.membership.granted_by.pickername
                    )
                if self.record_type == 'amend':
                    fact += ' ' + _("Edited by {actor}.").format(
                        actor=self.membership.granted_by.pickername
                    )

            return fact

        # --- Notification is being sent to other admins of the organization
        if self.record_type == 'direct_add':
            if self.membership.is_owner:
                return _(
                    "{user} was added as an owner of {organization} by {actor}."
                ).format(
                    user=self.membership.user.pickername,
                    organization=self.organization.pickername,
                    actor=self.membership.granted_by.pickername,
                )

            return _(
                "{user} was added as an admin of {organization} by {actor}."
            ).format(
                user=self.membership.user.pickername,
                organization=self.organization.pickername,
                actor=self.membership.granted_by.pickername,
            )
        if self.record_type == 'invite':
            if self.membership.is_owner:
                return _(
                    "{user} was invited to be an owner of {organization} by {actor}."
                ).format(
                    user=self.membership.user.pickername,
                    organization=self.organization.pickername,
                    actor=self.membership.granted_by.pickername,
                )

            return _(
                "{user} was invited to be an admin of {organization} by {actor}."
            ).format(
                user=self.membership.user.pickername,
                organization=self.organization.pickername,
                actor=self.membership.granted_by.pickername,
            )
        if self.record_type == 'accept':
            if self.membership.is_owner:
                return _("{user} is now an owner of {organization}.").format(
                    user=self.membership.user.pickername,
                    organization=self.organization.pickername,
                )

            return _("{user} is now an admin of {organization}.").format(
                user=self.membership.user.pickername,
                organization=self.organization.pickername,
            )
        if self.record_type == 'amend':
            if self.membership.is_owner:
                return _(
                    "{user} was changed to owner of {organization} by {actor}."
                ).format(
                    user=self.membership.user.pickername,
                    organization=self.organization.pickername,
                    actor=self.membership.granted_by.pickername,
                )

            return _(
                "{user} was changed to an admin of {organization} by {actor}."
            ).format(
                user=self.membership.user.pickername,
                organization=self.organization.pickername,
                actor=self.membership.granted_by.pickername,
            )

    def web(self):
        memberships = (
            self.user_notification.rolledup_fragments()
            .order_by(OrganizationMembership.granted_at.desc())
            .all()
        )
        return render_template(
            'notifications/organization_membership_granted_web.html.jinja2',
            view=self,
            memberships=memberships,
        )

    def email_subject(self):
        # Strip trailing period from email subject for English language style guide.
        # This may break localization in languages where the full stop is significant
        return f"🔑 {self.activity_fact()}".rstrip('.')

    def email_content(self):
        return render_template(
            'notifications/organization_membership_granted_email.html.jinja2', view=self
        )

    def sms(self):
        return _("Hi! {activity}").format(activity=self.activity_fact())


@OrganizationAdminMembershipRevokedNotification.renderer
class RenderOrganizationAdminMembershipRevokedNotification(RenderNotification):
    """Notify organization admins of removed admins."""

    aliases = {'document': 'organization', 'fragment': 'membership'}
    reason = __(
        "You are receiving this because you were an admin of this organization."
    )

    def activity_fact(self):
        """Return a single line summary of changes."""
        # --- Notification is being sent to the subject of the membership
        if self.user_notification.role == 'subject':
            if self.membership.user == self.membership.revoked_by:
                return _("You removed yourself as an admin of {organization}").format(
                    organization=self.organization.pickername
                )
            return _(
                "You were removed as an admin of {organization} by {actor}"
            ).format(
                organization=self.organization.pickername,
                actor=self.membership.revoked_by.pickername,
            )
        return _("{user} was removed as an admin of {organization} by {actor}").format(
            user=self.membership.user.pickername,
            organization=self.organization.pickername,
            actor=self.membership.revoked_by.pickername,
        )

    def web(self):
        return render_template(
            'notifications/organization_membership_revoked_web.html.jinja2', view=self
        )

    def email_subject(self):
        return f"🔑 {self.activity_fact()}"

    def email_content(self):
        return render_template(
            'notifications/organization_membership_revoked_email.html.jinja2', view=self
        )

    def sms(self):
        return _("Hi! {activity}").format(activity=self.activity_fact())
