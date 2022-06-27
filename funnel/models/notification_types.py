"""Notification types."""

from __future__ import annotations

from baseframe import __

from . import db
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
from .user import Organization, User

__all__ = [
    'AccountPasswordNotification',
    'NewUpdateNotification',
    'CommentReportReceivedNotification',
    'CommentReplyNotification',
    'NewCommentNotification',
    'ProposalReceivedNotification',
    'ProposalSubmittedNotification',
    'RegistrationCancellationNotification',
    'RegistrationConfirmationNotification',
    'ProjectStartingNotification',
    'OrganizationAdminMembershipNotification',
    'OrganizationAdminMembershipRevokedNotification',
]

# --- Mixin classes --------------------------------------------------------------------


class DocumentHasProject:
    """Mixin class for documents linked to a project."""

    document: db.Model

    @property
    def preference_context(self) -> Profile:
        """Return document's project's profile as preference context."""
        return self.document.project.profile


class DocumentHasProfile:
    """Mixin class for documents linked to a profile."""

    document: db.Model

    @property
    def preference_context(self) -> Profile:
        """Return document's profile as preference context."""
        return self.document.profile


# --- Account notifications ------------------------------------------------------------


class AccountPasswordNotification(Notification):
    """Notification when the user's password changes."""

    __mapper_args__ = {'polymorphic_identity': 'user_password_set'}
    category = notification_categories.account
    title = __("When my account password changes")
    description = __("For your safety, in case this was not authorized")

    document: User
    exclude_actor = False
    roles = ['owner']
    for_private_recipient = True


# --- Project participant notifications ------------------------------------------------


class RegistrationConfirmationNotification(DocumentHasProject, Notification):
    """Notification confirming registration to a project."""

    __mapper_args__ = {'polymorphic_identity': 'rsvp_yes'}
    category = notification_categories.participant
    title = __("When I register for a project")
    description = __("This will prompt a calendar entry in Gmail and other apps")

    document: Rsvp
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True


class RegistrationCancellationNotification(DocumentHasProject, Notification):
    """Notification confirming cancelling registration to a project."""

    __mapper_args__ = {'polymorphic_identity': 'rsvp_no'}
    category = notification_categories.participant
    title = __("When I cancel my registration")
    description = __("Confirmation for your records")

    document: Rsvp
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True
    allow_web = False


class NewUpdateNotification(DocumentHasProject, Notification):
    """Notifications of new updates."""

    __mapper_args__ = {'polymorphic_identity': 'update_new'}

    category = notification_categories.participant
    title = __("When a project posts an update")
    description = __(
        "Typically contains critical information such as video conference links"
    )

    document: Update
    roles = ['project_crew', 'project_participant']
    exclude_actor = False  # Send to everyone including the actor


class ProposalSubmittedNotification(DocumentHasProject, Notification):
    """Notification to the proposer on a successful proposal submission."""

    __mapper_args__ = {'polymorphic_identity': 'proposal_submitted'}

    category = notification_categories.participant
    title = __("When I submit a proposal")
    description = __("Confirmation for your records")

    document: Proposal
    roles = ['creator']
    exclude_actor = False  # This notification is for the actor

    # Email is typically fine. Messengers may be too noisy
    default_email = True
    default_sms = False
    default_webpush = False
    default_telegram = False
    default_whatsapp = False


class ProjectStartingNotification(DocumentHasProfile, Notification):
    """Notification of a session about to start."""

    __mapper_args__ = {'polymorphic_identity': 'project_starting'}

    category = notification_categories.participant
    title = __("When a project I’ve registered for is about to start")
    description = __("You will be notified 5-10 minutes before the starting time")

    document: Project
    fragment: Session
    roles = ['project_crew', 'project_participant']
    # This is a notification triggered without an actor


# --- Comment notifications ------------------------------------------------------------


class NewCommentNotification(Notification):
    """Notification of new comment."""

    __mapper_args__ = {'polymorphic_identity': 'comment_new'}

    category = notification_categories.participant
    title = __("When there is a new comment on a project or proposal I’m in")
    exclude_actor = True

    document: Commentset
    fragment: Comment
    roles = ['replied_to_commenter', 'document_subscriber']


class CommentReplyNotification(Notification):
    """Notification of comment replies."""

    __mapper_args__ = {'polymorphic_identity': 'comment_reply'}

    category = notification_categories.participant
    title = __("When someone replies to my comment")
    exclude_actor = True

    document: Comment  # Parent comment (being replied to)
    fragment: Comment  # Child comment (the reply that triggered notification)
    roles = ['replied_to_commenter']


# --- Project crew notifications -------------------------------------------------------


class ProjectCrewMembershipNotification(DocumentHasProject, Notification):
    """Notification of being granted crew membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'project_crew_membership_granted'}
    active = False

    category = notification_categories.project_crew
    title = __("When a project crew member is added, or roles change")
    description = __("Crew members have access to the project’s controls")

    document: Project
    fragment: ProjectCrewMembership
    roles = ['subject', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProjectCrewMembershipRevokedNotification(DocumentHasProject, Notification):
    """Notification of being granted crew membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'project_crew_membership_revoked'}
    active = False

    category = notification_categories.project_crew
    title = __("When a project crew member is removed, including me")

    document: Project
    fragment: ProjectCrewMembership
    roles = ['subject', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProposalReceivedNotification(DocumentHasProfile, Notification):
    """Notification to editors of new proposals."""

    __mapper_args__ = {'polymorphic_identity': 'proposal_received'}

    category = notification_categories.project_crew
    title = __("When my project receives a new proposal")

    document: Project
    fragment: Proposal
    roles = ['project_editor']
    exclude_actor = True  # Don't notify editor of proposal they submitted


class RegistrationReceivedNotification(DocumentHasProfile, Notification):
    """Notification to promoters of new registrations."""

    __mapper_args__ = {'polymorphic_identity': 'rsvp_received'}
    active = False

    category = notification_categories.project_crew
    title = __("When someone registers for my project")

    document: Project
    fragment: Rsvp
    roles = ['project_promoter']
    exclude_actor = True


# --- Organization admin notifications -------------------------------------------------


class OrganizationAdminMembershipNotification(DocumentHasProfile, Notification):
    """Notification of being granted admin membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'organization_membership_granted'}

    category = notification_categories.organization_admin
    title = __("When organization admins change")
    description = __("Organization admins control all projects under the organization")

    document: Organization
    fragment: OrganizationMembership
    roles = ['subject', 'profile_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class OrganizationAdminMembershipRevokedNotification(DocumentHasProfile, Notification):
    """Notification of being granted admin membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'organization_membership_revoked'}

    category = notification_categories.organization_admin
    title = __("When an organization admin is removed, including me")

    document: Organization
    fragment: OrganizationMembership
    roles = ['subject', 'profile_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


# --- Site administrator notifications -------------------------------------------------


class CommentReportReceivedNotification(Notification):
    """Notification for comment moderators when a comment is reported as spam."""

    __mapper_args__ = {'polymorphic_identity': 'comment_report_received'}

    category = notification_categories.site_admin
    title = __("When a comment is reported as spam")

    document: Comment
    fragment: CommentModeratorReport
    roles = ['comment_moderator']
