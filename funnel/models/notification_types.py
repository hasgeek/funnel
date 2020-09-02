from baseframe import __
from funnel.models.moderation import CommentModeratorReport

from .commentvote import Comment
from .notification import Notification, notification_categories
from .organization_membership import OrganizationMembership
from .project import Project
from .project_membership import ProjectCrewMembership
from .proposal import Proposal
from .rsvp import Rsvp
from .session import Session
from .update import Update
from .user import Organization

__all__ = [
    'CommentReportReceivedNotification',
    'NewUpdateNotification',
    'ProjectCommentNotification',
    'ProposalCommentNotification',
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
    @property
    def preference_context(self):
        return self.document.project.profile


class DocumentHasProfile:
    @property
    def preference_context(self):
        return self.document.profile


# --- Project participant notifications ------------------------------------------------


class RegistrationConfirmationNotification(DocumentHasProject, Notification):
    """Notification confirming registration to a project."""

    __mapper_args__ = {'polymorphic_identity': 'rsvp_yes'}
    category = notification_categories.participant
    title = __("When I register for a project")
    description = __("This will prompt a calendar entry in Gmail and other apps")

    document_model = Rsvp
    exclude_actor = False
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True


class RegistrationCancellationNotification(DocumentHasProject, Notification):
    """Notification confirming cancelling registration to a project."""

    __mapper_args__ = {'polymorphic_identity': 'rsvp_no'}
    category = notification_categories.participant
    title = __("When I cancel my registration")
    description = __("Confirmation for your records")

    document_model = Rsvp
    exclude_actor = False
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True


class NewUpdateNotification(DocumentHasProject, Notification):
    """Notifications of new updates."""

    __mapper_args__ = {'polymorphic_identity': 'update_new'}

    category = notification_categories.participant
    title = __("When a project posts an update")
    description = __(
        "Typically contains critical information such as video conference links"
    )

    document_model = Update
    roles = ['project_crew', 'project_participant']
    exclude_actor = False  # Send to everyone including the actor


class ProposalSubmittedNotification(DocumentHasProject, Notification):
    """Notification to the proposer on a successful proposal submission."""

    __mapper_args__ = {'polymorphic_identity': 'proposal_submitted'}

    category = notification_categories.participant
    title = __("When I submit a proposal")
    description = __("Confirmation for your records")

    document_model = Proposal
    roles = ['creator']
    exclude_actor = False  # This notification is for the actor
    for_private_recipient = True

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

    document_model = Project
    fragment_model = Session
    roles = ['project_crew', 'project_participant']
    # This is a notification triggered without an actor


# --- Comment notifications ------------------------------------------------------------


class CommentReplyNotification(Notification):
    """Notification of comment replies."""

    __mapper_args__ = {'polymorphic_identity': 'comment_reply'}
    active = False

    category = notification_categories.participant
    title = __("When someone replies to my comment")
    exclude_actor = True

    document_model = Comment  # Parent comment (being replied to)
    fragment_model = Comment  # Child comment (the reply that triggered notification)
    roles = ['replied_to_commenter']


class ProposalCommentNotification(DocumentHasProject, Notification):
    """Notification of comments on a proposal."""

    __mapper_args__ = {'polymorphic_identity': 'comment_proposal'}
    active = False

    category = notification_categories.participant
    title = __("When my proposal receives a comment")
    exclude_actor = True

    document_model = Proposal
    fragment_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # fragment if present, document if not.
    roles = ['presenter', 'replied_to_commenter']  # FIXME: Role may still be 'speaker'


class ProjectCommentNotification(DocumentHasProfile, Notification):
    """Notification of comments on a proposal."""

    __mapper_args__ = {'polymorphic_identity': 'comment_project'}
    active = False

    category = notification_categories.project_crew
    title = __("When my project receives a comment")
    exclude_actor = True

    document_model = Project
    fragment_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # fragment if present, document if not.
    roles = ['project_editor', 'replied_to_commenter']


# --- Project crew notifications -------------------------------------------------------


class ProjectCrewMembershipNotification(DocumentHasProject, Notification):
    """Notification of being granted crew membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'project_crew_membership_granted'}
    active = False

    category = notification_categories.project_crew
    title = __("When a project crew member is added, or roles change")
    description = __("Crew members have access to the project’s controls")

    document_model = Project
    fragment_model = ProjectCrewMembership
    roles = ['subject', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProjectCrewMembershipRevokedNotification(DocumentHasProject, Notification):
    """Notification of being granted crew membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'project_crew_membership_revoked'}
    active = False

    category = notification_categories.project_crew
    title = __("When a project crew member is removed, including me")

    document_model = Project
    fragment_model = ProjectCrewMembership
    roles = ['subject', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProposalReceivedNotification(DocumentHasProfile, Notification):
    """Notification to editors of new proposals."""

    __mapper_args__ = {'polymorphic_identity': 'proposal_received'}

    category = notification_categories.project_crew
    title = __("When my project receives a new proposal")

    document_model = Project
    fragment_model = Proposal
    roles = ['project_editor']
    exclude_actor = True  # Don't notify editor of proposal they submitted


class RegistrationReceivedNotification(DocumentHasProfile, Notification):
    """Notification to concierges of new registrations."""

    __mapper_args__ = {'polymorphic_identity': 'rsvp_received'}
    active = False

    category = notification_categories.project_crew
    title = __("When someone registers for my project")

    document_model = Project
    fragment_model = Rsvp
    roles = ['project_concierge']
    exclude_actor = True


# --- Organization admin notifications -------------------------------------------------


class OrganizationAdminMembershipNotification(DocumentHasProfile, Notification):
    """Notification of being granted admin membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'organization_membership_granted'}

    category = notification_categories.organization_admin
    title = __("When organization admins change")
    description = __("Organization admins control all projects under the organization")

    document_model = Organization
    fragment_model = OrganizationMembership
    roles = ['subject', 'profile_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class OrganizationAdminMembershipRevokedNotification(DocumentHasProfile, Notification):
    """Notification of being granted admin membership (including role changes)."""

    __mapper_args__ = {'polymorphic_identity': 'organization_membership_revoked'}

    category = notification_categories.organization_admin
    title = __("When an organization admin is removed, including me")

    document_model = Organization
    fragment_model = OrganizationMembership
    roles = ['subject', 'profile_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class CommentReportReceivedNotification(Notification):
    """Notification for site editors when a comment is reported as spam"""

    __mapper_args__ = {'polymorphic_identity': 'comment_report_received'}

    category = notification_categories.site_admin
    title = __("When a comment is reported as spam")

    document_model = Comment
    fragment_model = CommentModeratorReport
    roles = ['site_editor']
