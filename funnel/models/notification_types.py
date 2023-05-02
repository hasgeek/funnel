"""Notification types."""

from __future__ import annotations

from baseframe import __

from ..typing import UuidModelType
from . import Mapped
from .account import Account, Organization, User
from .comment import Comment, Commentset
from .moderation import CommentModeratorReport
from .notification import Notification, notification_categories
from .organization_membership import OrganizationMembership
from .profile import Profile
from .project import Project
from .project_membership import ProjectCrewMembership
from .proposal import Proposal
from .rsvp import Rsvp
from .session import Session
from .update import Update

__all__ = [
    'AccountPasswordNotification',
    'NewUpdateNotification',
    'CommentReportReceivedNotification',
    'CommentReplyNotification',
    'NewCommentNotification',
    'ProjectCrewMembershipNotification',
    'ProjectCrewMembershipRevokedNotification',
    'ProposalReceivedNotification',
    'ProposalSubmittedNotification',
    'RegistrationCancellationNotification',
    'RegistrationConfirmationNotification',
    'ProjectStartingNotification',
    'OrganizationAdminMembershipNotification',
    'OrganizationAdminMembershipRevokedNotification',
]

# --- Protocol and Mixin classes -------------------------------------------------------


class AccountSubtype(UuidModelType):
    """Model that links to an account."""

    profile: Mapped[Account]


class ProjectSubtype(UuidModelType):
    """Model that links to a project."""

    project: Mapped[Project]


class DocumentHasProject:
    """Mixin class for documents linked to a project."""

    document: ProjectSubtype

    @property
    def preference_context(self) -> Profile:
        """Return document's project's account as preference context."""
        return self.document.project.account


class DocumentHasProfile:
    """Mixin class for documents linked to an account (nee profile)."""

    document: AccountSubtype

    @property
    def preference_context(self) -> Profile:
        """Return document's account as preference context."""
        return self.document.profile


# --- Account notifications ------------------------------------------------------------


class AccountPasswordNotification(Notification, type='user_password_set'):
    """Notification when the user's password changes."""

    category = notification_categories.account
    title = __("When my account password changes")
    description = __("For your safety, in case this was not authorized")

    document_model = User
    exclude_actor = False
    roles = ['owner']
    for_private_recipient = True


# --- Project participant notifications ------------------------------------------------


class RegistrationConfirmationNotification(
    DocumentHasProject, Notification, type='rsvp_yes'
):
    """Notification confirming registration to a project."""

    category = notification_categories.participant
    title = __("When I register for a project")
    description = __("This will prompt a calendar entry in Gmail and other apps")

    document_model = Rsvp
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True


class RegistrationCancellationNotification(
    DocumentHasProject,
    Notification,
    type='rsvp_no',
    shadows=RegistrationConfirmationNotification,
):
    """Notification confirming cancelling registration to a project."""

    document_model = Rsvp
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True
    allow_web = False


class NewUpdateNotification(DocumentHasProject, Notification, type='update_new'):
    """Notifications of new updates."""

    category = notification_categories.participant
    title = __("When a project posts an update")
    description = __(
        "Typically contains critical information such as video conference links"
    )

    document_model = Update
    roles = ['project_crew', 'project_participant']
    exclude_actor = False  # Send to everyone including the actor


class ProposalSubmittedNotification(
    DocumentHasProject, Notification, type='proposal_submitted'
):
    """Notification to the proposer on a successful proposal submission."""

    category = notification_categories.participant
    title = __("When I submit a proposal")
    description = __("Confirmation for your records")

    document_model = Proposal
    roles = ['creator']
    exclude_actor = False  # This notification is for the actor

    # Email is typically fine. Messengers may be too noisy
    default_email = True
    default_sms = False
    default_webpush = False
    default_telegram = False
    default_whatsapp = False


class ProjectStartingNotification(
    DocumentHasProfile, Notification, type='project_starting'
):
    """Notification of a session about to start."""

    category = notification_categories.participant
    title = __("When a project I’ve registered for is about to start")
    description = __("You will be notified 5-10 minutes before the starting time")

    document_model = Project
    fragment_model = Session
    roles = ['project_crew', 'project_participant']
    # This is a notification triggered without an actor


# --- Comment notifications ------------------------------------------------------------


class NewCommentNotification(Notification, type='comment_new'):
    """Notification of new comment."""

    category = notification_categories.participant
    title = __("When there is a new comment on something I’m involved in")
    exclude_actor = True

    document_model = Commentset
    fragment_model = Comment
    roles = ['replied_to_commenter', 'document_subscriber']


class CommentReplyNotification(Notification, type='comment_reply'):
    """Notification of comment replies and mentions."""

    category = notification_categories.participant
    title = __("When someone replies to my comment or mentions me")
    exclude_actor = True

    document_model = Comment  # Parent comment (being replied to)
    fragment_model = Comment  # Child comment (the reply that triggered notification)
    roles = ['replied_to_commenter']


# --- Project crew notifications -------------------------------------------------------


class ProjectCrewMembershipNotification(
    DocumentHasProfile, Notification, type='project_crew_membership_granted'
):
    """Notification of being granted crew membership (including role changes)."""

    category = notification_categories.project_crew
    title = __("When a project crew member is added or removed")
    description = __("Crew members have access to the project’s settings and data")

    document_model = Project
    fragment_model = ProjectCrewMembership
    roles = ['member', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProjectCrewMembershipRevokedNotification(
    DocumentHasProfile,
    Notification,
    type='project_crew_membership_revoked',
    shadows=ProjectCrewMembershipNotification,
):
    """Notification of being removed from crew membership (including role changes)."""

    document_model = Project
    fragment_model = ProjectCrewMembership
    roles = ['member', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProposalReceivedNotification(
    DocumentHasProfile, Notification, type='proposal_received'
):
    """Notification to editors of new proposals."""

    category = notification_categories.project_crew
    title = __("When my project receives a new proposal")

    document_model = Project
    fragment_model = Proposal
    roles = ['project_editor']
    exclude_actor = True  # Don't notify editor of proposal they submitted


class RegistrationReceivedNotification(
    DocumentHasProfile, Notification, type='rsvp_received'
):
    """Notification to promoters of new registrations."""

    active = False

    category = notification_categories.project_crew
    title = __("When someone registers for my project")

    document_model = Project
    fragment_model = Rsvp
    roles = ['project_promoter']
    exclude_actor = True


# --- Organization admin notifications -------------------------------------------------


class OrganizationAdminMembershipNotification(
    DocumentHasProfile, Notification, type='organization_membership_granted'
):
    """Notification of being granted admin membership (including role changes)."""

    category = notification_categories.account_admin
    title = __("When account admins change")
    description = __("Account admins control all projects under the account")

    document_model = Organization
    fragment_model = OrganizationMembership
    roles = ['member', 'account_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class OrganizationAdminMembershipRevokedNotification(
    DocumentHasProfile,
    Notification,
    type='organization_membership_revoked',
    shadows=OrganizationAdminMembershipNotification,
):
    """Notification of being granted admin membership (including role changes)."""

    document_model = Organization
    fragment_model = OrganizationMembership
    roles = ['member', 'account_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


# --- Site administrator notifications -------------------------------------------------


class CommentReportReceivedNotification(Notification, type='comment_report_received'):
    """Notification for comment moderators when a comment is reported as spam."""

    category = notification_categories.site_admin
    title = __("When a comment is reported as spam")

    document_model = Comment
    fragment_model = CommentModeratorReport
    roles = ['comment_moderator']
