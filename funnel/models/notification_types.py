from baseframe import __

from .commentvote import Comment
from .notification import NOTIFICATION_CATEGORY, Notification
from .project import Project
from .proposal import Proposal
from .update import Update

__all__ = [
    'NewUpdateNotification',
    'NewProposalNotification',
    'ProposalCommentNotification',
    'ProjectCommentNotification',
]

# --- Model-specific notifications -----------------------------------------------------


class NewUpdateNotification(Notification):
    """
    Notifications of new updates.
    """

    __mapper_args__ = {'polymorphic_identity': 'update_new'}

    category = NOTIFICATION_CATEGORY.PARTICIPANT
    description = __("When a project posts an update")

    document_model = Update
    roles = ['project_crew', 'project_participant']

    @property
    def preference_context(self):
        return self.document.project.profile


class NewProposalNotification(Notification):
    """
    Notifications of new proposals.
    """

    __mapper_args__ = {'polymorphic_identity': 'proposal_new'}

    category = NOTIFICATION_CATEGORY.PROJECT_CREW
    description = __("When my project receives a new proposal")

    document_model = Proposal
    roles = ['project_editor', 'project_participant']

    @property
    def preference_context(self):
        return self.document.project.profile


# --- Notifications with targets


class ProposalCommentNotification(Notification):
    """
    Notification of comments on a proposal.
    """

    __mapper_args__ = {'polymorphic_identity': 'proposal_comment'}

    category = NOTIFICATION_CATEGORY.PARTICIPANT
    description = __("When my proposal receives a comment")

    document_model = Proposal
    target_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # target if present, document if not.
    roles = ['presenter', 'mentioned_commenter']

    @property
    def preference_context(self):
        return self.document.project.profile


class ProjectCommentNotification(Notification):
    """
    Notification of comments on a proposal.
    """

    __mapper_args__ = {'polymorphic_identity': 'project_comment'}

    category = NOTIFICATION_CATEGORY.PROJECT_CREW
    description = __("When my project receives a comment")

    document_model = Project
    target_model = Comment
    # Note: These roles must be available on Comment, not Proposal. Roles come from
    # target if present, document if not.
    roles = ['project_editor', 'mentioned_commenter']

    @property
    def preference_context(self):
        return self.document.profile
