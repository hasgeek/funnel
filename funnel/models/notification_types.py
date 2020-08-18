from baseframe import __

from .commentvote import Comment
from .notification import NOTIFICATION_CATEGORY, Notification
from .project import Project
from .proposal import Proposal
from .rsvp import Rsvp
from .update import Update

__all__ = [
    'NewProposalNotification',
    'NewUpdateNotification',
    'ProjectCommentNotification',
    'ProposalCommentNotification',
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
    description = __("When I register for a project")

    document_model = Rsvp
    exclude_user = False
    roles = ['owner']


class RegistrationCancellationNotification(ProjectIsParent, Notification):
    """
    Notification confirming cancelling registration to a project.
    """

    __mapper_args__ = {'polymorphic_identity': 'rsvp_no'}
    category = NOTIFICATION_CATEGORY.PARTICIPANT
    description = __("When I cancel my registration")

    document_model = Rsvp
    exclude_user = False
    roles = ['owner']


class NewUpdateNotification(ProjectIsParent, Notification):
    """
    Notifications of new updates.
    """

    __mapper_args__ = {'polymorphic_identity': 'update_new'}

    category = NOTIFICATION_CATEGORY.PARTICIPANT
    description = __("When a project posts an update")

    document_model = Update
    roles = ['project_crew', 'project_participant']


class NewProposalNotification(ProjectIsParent, Notification):
    """
    Notifications of new proposals.
    """

    __mapper_args__ = {'polymorphic_identity': 'proposal_new'}

    category = NOTIFICATION_CATEGORY.PROJECT_CREW
    description = __("When my project receives a new proposal")

    document_model = Proposal
    roles = ['project_editor', 'project_participant']


# --- Notifications with fragments -----------------------------------------------------


class ProposalCommentNotification(ProjectIsParent, Notification):
    """
    Notification of comments on a proposal.
    """

    __mapper_args__ = {'polymorphic_identity': 'proposal_comment'}

    category = NOTIFICATION_CATEGORY.PARTICIPANT
    description = __("When my proposal receives a comment")

    document_model = Proposal
    fragment_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # fragment if present, document if not.
    roles = ['presenter', 'mentioned_commenter']


class ProjectCommentNotification(ProfileIsParent, Notification):
    """
    Notification of comments on a proposal.
    """

    __mapper_args__ = {'polymorphic_identity': 'project_comment'}

    category = NOTIFICATION_CATEGORY.PROJECT_CREW
    description = __("When my project receives a comment")

    document_model = Project
    fragment_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # fragment if present, document if not.
    roles = ['project_editor', 'mentioned_commenter']
