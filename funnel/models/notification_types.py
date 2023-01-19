"""Notification types."""

from __future__ import annotations

from typing import ClassVar, Dict
from uuid import UUID

from typing_extensions import Protocol

from baseframe import __

from ..typing import Mapped, UuidModelType
from . import db
from .comment import Comment, Commentset
from .moderation import CommentModeratorReport
from .notification import Notification, Role, notification_categories
from .organization_membership import OrganizationMembership
from .profile import Profile
from .project import Project
from .project_membership import ProjectCrewMembership
from .proposal import Proposal
from .rsvp import Rsvp
from .session import Session
from .update import Update
from .user import Organization, User

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


# --- Role definitions -----------------------------------------------------------------


role_profile_owner = Role('profile_owner', __("Account owner"))
role_profile_admin = Role('profile_admin', __("Account administrator"))
role_project_participant = Role('project_participant', __("Project participant"))
role_project_crew = Role('project_crew', __("All project crew"))
role_project_editor = Role('project_editor', __("Project editor"))
role_project_promoter = Role('project_promoter', __("Project promoter"))
role_document_subscriber = Role('document_subscriber', __("Document subscriber"))


# --- Protocol and Mixin classes -------------------------------------------------------


class ProfileSubtype(UuidModelType):
    """Model that links to an account (nee profile)."""

    profile: Mapped[Profile]


class ProjectSubtype(UuidModelType):
    """Model that links to a project."""

    project: Mapped[Project]


class NotificationDocumentProtocol(Protocol):
    """Protocol class for notifications with a linked document."""

    document_type: ClassVar[str]
    document: db.Model  # type: ignore[name-defined]
    document_uuid: UUID


class DocumentHasProject:
    """Mixin class for documents linked to a project."""

    document: ProjectSubtype

    @property
    def preference_context(self: NotificationDocumentProtocol) -> Profile:
        """Return document's project's account as preference context."""
        return self.document.project.profile

    def hook_context_uuids(self: NotificationDocumentProtocol) -> Dict[str, UUID]:
        """Return UUIDs of current and parent documents for notification hook hosts."""
        project = self.document.project
        return {
            self.document_type: self.document_uuid,
            'project': project.uuid,
            'profile': project.profile.uuid,
        }


class DocumentHasProfile:
    """Mixin class for documents linked to an account (nee profile)."""

    document: ProfileSubtype

    @property
    def preference_context(self: NotificationDocumentProtocol) -> Profile:
        """Return document's account as preference context."""
        return self.document.profile

    def hook_context_uuids(self: NotificationDocumentProtocol) -> Dict[str, UUID]:
        """Return UUIDs of current and parent documents for notification hook hosts."""
        return {
            self.document_type: self.document_uuid,  # type: ignore[attr-defined]
            'profile': self.document.profile.uuid,
        }


# --- Account notifications ------------------------------------------------------------


class AccountPasswordNotification(Notification, type='user_password_set'):
    """Notification when the user's password changes."""

    category = notification_categories.account
    title = __("When my account password changes")
    description = __("For your safety, in case this was not authorized")

    document: User
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

    document: Rsvp
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

    document: Rsvp
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

    document: Update
    roles = ['project_crew', 'project_participant']
    shared_roles = {
        'project_crew': role_project_crew,
        'project_participant': role_project_participant,
    }
    exclude_actor = False  # Send to everyone including the actor


class ProposalSubmittedNotification(
    DocumentHasProject, Notification, type='proposal_submitted'
):
    """Notification to the proposer on a successful proposal submission."""

    category = notification_categories.participant
    title = __("When I make a submission")
    description = __("Confirmation for your records")

    document: Proposal
    roles = ['creator']  # TODO: Change this to include collaborators
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

    document: Project
    fragment: Session
    roles = ['project_crew', 'project_participant']
    shared_roles = {
        'project_crew': role_project_crew,
        'project_participant': role_project_participant,
    }
    # This is a notification triggered without an actor


# --- Comment notifications ------------------------------------------------------------


class NewCommentNotification(Notification, type='comment_new'):
    """Notification of new comment."""

    category = notification_categories.participant
    title = __("When there is a new comment on something I’m involved in")
    exclude_actor = True

    document: Commentset
    fragment: Comment
    roles = ['replied_to_commenter', 'document_subscriber']
    shared_roles = {'document_subscriber': role_document_subscriber}


class CommentReplyNotification(Notification, type='comment_reply'):
    """Notification of comment replies and mentions."""

    category = notification_categories.participant
    title = __("When someone replies to my comment or mentions me")
    exclude_actor = True

    document: Comment  # Parent comment (being replied to)
    fragment: Comment  # Child comment (the reply that triggered notification)
    roles = ['replied_to_commenter']


# --- Project crew notifications -------------------------------------------------------


class ProjectCrewMembershipNotification(
    DocumentHasProfile, Notification, type='project_crew_membership_granted'
):
    """Notification of being granted crew membership (including role changes)."""

    category = notification_categories.project_crew
    title = __("When a project crew member is added or removed")
    description = __("Crew members have access to the project’s settings and data")

    document: Project
    fragment: ProjectCrewMembership
    roles = ['subject', 'project_crew']
    shared_roles = {'project_crew': role_project_crew}
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProjectCrewMembershipRevokedNotification(
    DocumentHasProfile,
    Notification,
    type='project_crew_membership_revoked',
    shadows=ProjectCrewMembershipNotification,
):
    """Notification of being removed from crew membership (including role changes)."""

    document: Project
    fragment: ProjectCrewMembership
    roles = ['subject', 'project_crew']
    shared_roles = {'project_crew': role_project_crew}
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProposalReceivedNotification(
    DocumentHasProfile, Notification, type='proposal_received'
):
    """Notification to editors of new proposals."""

    category = notification_categories.project_crew
    title = __("When my project receives a new proposal")

    document: Project
    fragment: Proposal
    roles = ['project_editor']
    shared_roles = {'project_editor': role_project_editor}
    exclude_actor = True  # Don't notify editor of proposal they submitted


class RegistrationReceivedNotification(
    DocumentHasProfile, Notification, type='rsvp_received'
):
    """Notification to promoters of new registrations."""

    active = False

    category = notification_categories.project_crew
    title = __("When someone registers for my project")

    document: Project
    fragment: Rsvp
    roles = ['project_promoter']
    shared_roles = {'project_promoter': role_project_promoter}
    exclude_actor = True


# --- Organization admin notifications -------------------------------------------------


class OrganizationAdminMembershipNotification(
    DocumentHasProfile, Notification, type='organization_membership_granted'
):
    """Notification of being granted admin membership (including role changes)."""

    category = notification_categories.account_admin
    title = __("When account admins change")
    description = __("Account admins control all projects under the account")

    document: Organization
    fragment: OrganizationMembership
    roles = ['subject', 'profile_admin']
    shared_roles = {'profile_admin': role_profile_admin}
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class OrganizationAdminMembershipRevokedNotification(
    DocumentHasProfile,
    Notification,
    type='organization_membership_revoked',
    shadows=OrganizationAdminMembershipNotification,
):
    """Notification of being granted admin membership (including role changes)."""

    document: Organization
    fragment: OrganizationMembership
    roles = ['subject', 'profile_admin']
    shared_roles = {'profile_admin': role_profile_admin}
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


# --- Site administrator notifications -------------------------------------------------


class CommentReportReceivedNotification(Notification, type='comment_report_received'):
    """Notification for comment moderators when a comment is reported as spam."""

    category = notification_categories.site_admin
    title = __("When a comment is reported as spam")

    document: Comment
    fragment: CommentModeratorReport
    roles = ['comment_moderator']
    shared_roles = {
        'comment_moderator': Role('comment_moderator', __("Comment moderator"))
    }


# TODO: Add shared role hook models and document ids
# TODO: new models: NotificationHook (links to host document_id on behalf of one user)
# TODO: HookTarget -- with polymorphic subtypes, links NotificationHook to destination
# TODO: destination types: email, telegram group, slack bot, signal bot, other?
# TODO: eventid + hook target unique constraint, so that multiple hooks leading to the
# TODO: same destination are deduped and only one notification is sent.
# TODO: Hook must specify multiple notification types + roles and be quick to discover.
# TODO: How? PG array with indexing? JSON struct with indexing?
