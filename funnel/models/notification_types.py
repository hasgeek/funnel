from baseframe import __

from .commentvote import Comment
from .notification import NOTIFICATION_CATEGORY, Notification
from .project import Project
from .proposal import Proposal
from .rsvp import Rsvp
from .update import Update

__all__ = [
    'NewUpdateNotification',
    'ProjectCommentNotification',
    'ProposalCommentNotification',
    'ProposalReceivedNotification',
    'ProposalSubmittedNotification',
    'RegistrationCancellationNotification',
    'RegistrationConfirmationNotification',
]

# --- Mixin classes --------------------------------------------------------------------


class ProjectIsParent:
    @property
    def preference_context(self):
        return self.document.project.profile


class ProfileIsParent:
    @property
    def preference_context(self):
        return self.document.profile


# --- Project notifications ------------------------------------------------------------


class RegistrationConfirmationNotification(ProjectIsParent, Notification):
    """
    Notification confirming registration to a project.
    """

    __mapper_args__ = {'polymorphic_identity': 'rsvp_yes'}
    category = NOTIFICATION_CATEGORY.PARTICIPANT
    title = __("When I register for a project")
    description = __("This will prompt a calendar entry in Gmail and other apps.")

    document_model = Rsvp
    exclude_actor = False
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor


class RegistrationCancellationNotification(ProjectIsParent, Notification):
    """
    Notification confirming cancelling registration to a project.
    """

    __mapper_args__ = {'polymorphic_identity': 'rsvp_no'}
    category = NOTIFICATION_CATEGORY.PARTICIPANT
    title = __("When I cancel my registration")

    document_model = Rsvp
    exclude_actor = False
    roles = ['owner']
    exclude_actor = False  # This is a notification to the actor


class NewUpdateNotification(ProjectIsParent, Notification):
    """
    Notifications of new updates.
    """

    __mapper_args__ = {'polymorphic_identity': 'update_new'}

    category = NOTIFICATION_CATEGORY.PARTICIPANT
    title = __("When a project posts an update")
    description = __(
        "Typically contains critical information such as video conference links"
    )

    document_model = Update
    roles = ['project_crew', 'project_participant']
    exclude_actor = False  # Send to everyone including the actor


class ProposalReceivedNotification(ProfileIsParent, Notification):
    """
    Notification to editors of new proposals.
    """

    __mapper_args__ = {'polymorphic_identity': 'proposal_received'}

    category = NOTIFICATION_CATEGORY.PROJECT_CREW
    title = __("When my project receives a new proposal")

    document_model = Project
    fragment_model = Proposal
    roles = ['project_editor']
    exclude_actor = True  # Don't notify editor of proposal they submitted


class ProposalSubmittedNotification(ProjectIsParent, Notification):
    """
    Notification to the proposer on a successful proposal submission.
    """

    __mapper_args__ = {'polymorphic_identity': 'proposal_submitted'}

    category = NOTIFICATION_CATEGORY.PARTICIPANT
    title = __("When I submit a proposal")

    document_model = Proposal
    roles = ['creator']
    exclude_actor = False  # This notification is for the actor

    # Email is typically fine. Messengers may be too noisy
    default_email = True
    default_sms = False
    default_webpush = False
    default_telegram = False
    default_whatsapp = False


# --- Notifications with fragments -----------------------------------------------------


class ProposalCommentNotification(ProjectIsParent, Notification):
    """
    Notification of comments on a proposal.
    """

    __mapper_args__ = {'polymorphic_identity': 'proposal_comment'}

    category = NOTIFICATION_CATEGORY.PARTICIPANT
    title = __("When my proposal receives a comment")
    exclude_actor = True

    document_model = Proposal
    fragment_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # fragment if present, document if not.
    roles = ['presenter', 'repliedto_commenter']


class ProjectCommentNotification(ProfileIsParent, Notification):
    """
    Notification of comments on a proposal.
    """

    __mapper_args__ = {'polymorphic_identity': 'project_comment'}

    category = NOTIFICATION_CATEGORY.PROJECT_CREW
    title = __("When my project receives a comment")
    exclude_actor = True

    document_model = Project
    fragment_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # fragment if present, document if not.
    roles = ['project_editor', 'repliedto_commenter']
