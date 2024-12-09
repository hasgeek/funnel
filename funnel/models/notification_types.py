"""Notification types."""

# Pyright complains that a property in the base class (for `roles`) has become a
# classvar in the subclass. Mypy does not. Silence Pyright here

# pyright: reportAssignmentType=false

from __future__ import annotations

from baseframe import __

from .account import Account
from .account_membership import AccountMembership
from .comment import Comment, Commentset
from .moderation import CommentModeratorReport
from .notification import Notification, notification_categories
from .project import Project
from .project_membership import ProjectMembership
from .proposal import Proposal
from .rsvp import Rsvp
from .session import Session
from .update import Update

__all__ = [
    'AccountAdminNotification',
    'AccountAdminRevokedNotification',
    'AccountPasswordNotification',
    'CommentReplyNotification',
    'CommentReportReceivedNotification',
    'NewCommentNotification',
    'ProjectCrewNotification',
    'ProjectCrewRevokedNotification',
    'ProjectStartingNotification',
    'ProjectTomorrowNotification',
    'ProjectUpdateNotification',
    'ProposalReceivedNotification',
    'ProposalSubmittedNotification',
    'RegistrationCancellationNotification',
    'RegistrationConfirmationNotification',
]

# MARK: Protocol and Mixin classes -----------------------------------------------------


class DocumentHasProject:
    """Mixin class for documents linked to a project."""

    @property
    def preference_context(self) -> Account:
        """Return document's project's account as preference context."""
        return self.document.project.account  # type: ignore[attr-defined]


class DocumentHasAccount:
    """Mixin class for documents linked to an account."""

    @property
    def preference_context(self) -> Account:
        """Return document's account as preference context."""
        return self.document.account  # type: ignore[attr-defined]


class DocumentIsAccount:
    """Mixin class for when the account is the document."""

    @property
    def preference_context(self) -> Account:
        """Return document itself as preference context."""
        return self.document  # type: ignore[attr-defined]


# MARK: Account notifications ----------------------------------------------------------


class AccountPasswordNotification(
    DocumentIsAccount, Notification[Account, None], type='user_password_set'
):
    """Notification when the user's password changes."""

    category = notification_categories.account
    title = __("When my account password changes")
    description = __("For your attention, in case this was not authorized")

    exclude_actor = False
    dispatch_roles = ['owner']
    for_private_recipient = True


class FollowerNotification(
    DocumentIsAccount, Notification[Account, AccountMembership], type='follower'
):
    """Notification of a new follower."""

    active = False

    category = notification_categories.account
    title = __("When I have a new follower")
    description = __("See who is interested in your work")

    exclude_actor = True  # The actor can't possibly receive this notification anyway
    dispatch_roles = ['account_admin']


# MARK: Project participant notifications ----------------------------------------------


class RegistrationConfirmationNotification(
    DocumentHasProject, Notification[Rsvp, None], type='rsvp_yes'
):
    """Notification confirming registration to a project."""

    category = notification_categories.participant
    title = __("When I register for a session")
    description = __("This will prompt a calendar entry in Gmail and other apps")

    dispatch_roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True


class RegistrationCancellationNotification(
    DocumentHasProject,
    Notification[Rsvp, None],
    type='rsvp_no',
    shadows=RegistrationConfirmationNotification,
):
    """Notification confirming cancelling registration to a project."""

    dispatch_roles = ['owner']
    exclude_actor = False  # This is a notification to the actor
    for_private_recipient = True
    allow_web = False


class ProjectUpdateNotification(
    DocumentHasAccount, Notification[Project, Update], type='project_update'
):
    """Notification of a new update in a project."""

    category = notification_categories.participant
    title = __("When there is an update")
    description = __(
        "Typically contains critical information such as video conference links"
    )

    exclude_actor = False  # Send to everyone including the actor

    @property
    def dispatch_roles(self) -> list[str]:
        """Target roles based on Update visibility state."""
        # TODO: Use match/case matching here. If states use a Python Enum, Mypy will
        # do an exhaustiveness check, so the closing RuntimeError is not needed.
        # https://github.com/python/mypy/issues/6366
        visibility = self.fragment.visibility_state
        if visibility.PUBLIC:
            return ['project_crew', 'project_participant', 'account_follower']
        if visibility.PARTICIPANTS:
            return ['project_crew', 'project_participant']
        if visibility.MEMBERS:
            return ['project_crew', 'project_participant', 'account_member']

        raise RuntimeError("Unknown update visibility state")


class ProposalSubmittedNotification(
    DocumentHasProject, Notification[Proposal, None], type='proposal_submitted'
):
    """Notification to the proposer on a successful proposal submission."""

    category = notification_categories.participant
    title = __("When I submit a proposal")
    description = __("Confirmation for your records")

    dispatch_roles = ['creator']
    exclude_actor = False  # This notification is for the actor

    # Email is typically fine. Messengers may be too noisy
    default_email = True
    default_sms = False
    default_webpush = False
    default_telegram = False
    default_whatsapp = False


class ProjectStartingNotification(
    DocumentHasAccount,
    Notification[Project, Session | None],
    type='project_starting',
):
    """Notification of a session about to start."""

    category = notification_categories.participant
    title = __("When a session is starting soon")
    description = __(
        "You will be notified shortly before an online session, or a day before an"
        " in-person session"
    )

    dispatch_roles = ['project_crew', 'project_participant']
    # This is a notification triggered without an actor


class ProjectTomorrowNotification(
    DocumentHasAccount,
    Notification[Project, Session | None],
    type='project_tomorrow',
    shadows=ProjectStartingNotification,
):
    """Notification of an in-person session the next day."""

    dispatch_roles = ['project_crew', 'project_participant']
    # This is a notification triggered without an actor


# MARK: Comment notifications ----------------------------------------------------------


class NewCommentNotification(Notification[Commentset, Comment], type='comment_new'):
    """Notification of new comment."""

    category = notification_categories.participant
    title = __("When there is a new comment on something I’m involved in")
    exclude_actor = True

    dispatch_roles = ['replied_to_commenter', 'document_subscriber']


class CommentReplyNotification(Notification[Comment, Comment], type='comment_reply'):
    """Notification of comment replies and mentions."""

    category = notification_categories.participant
    title = __("When someone replies to my comment or mentions me")
    exclude_actor = True

    # document_model = Parent comment (being replied to)
    # fragment_model = Child comment (the reply that triggered notification)
    dispatch_roles = ['replied_to_commenter']


# MARK: Project crew notifications -----------------------------------------------------


class ProjectCrewNotification(
    DocumentHasAccount,
    Notification[Project, ProjectMembership],
    type='project_crew',
):
    """Notification of being granted crew membership (including role changes)."""

    category = notification_categories.project_crew
    title = __("When crew members change")
    description = __("Crew members have access to the project’s settings and data")

    dispatch_roles = ['member', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProjectCrewRevokedNotification(
    DocumentHasAccount,
    Notification[Project, ProjectMembership],
    type='project_crew_revoked',
    shadows=ProjectCrewNotification,
):
    """Notification of being removed from crew membership (including role changes)."""

    dispatch_roles = ['member', 'project_crew']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class ProposalReceivedNotification(
    DocumentHasAccount, Notification[Project, Proposal], type='proposal_received'
):
    """Notification to editors of new proposals."""

    category = notification_categories.project_crew
    title = __("When my project receives a new proposal")

    dispatch_roles = ['project_editor']
    exclude_actor = True  # Don't notify editor of proposal they submitted


class RegistrationReceivedNotification(
    DocumentHasAccount, Notification[Project, Rsvp], type='rsvp_received'
):
    """Notification to promoters of new registrations."""

    active = False

    category = notification_categories.project_crew
    title = __("When someone registers for my project")

    dispatch_roles = ['project_promoter']
    exclude_actor = True


# MARK: Account admin notifications ----------------------------------------------------


class AccountAdminNotification(
    DocumentIsAccount,
    Notification[Account, AccountMembership],
    type='account_admin',
):
    """Notification of being granted admin membership (including role changes)."""

    category = notification_categories.account_admin
    title = __("When account admins change")
    description = __("Account admins control all projects under the account")

    # Notify the affected individual and all account admins
    dispatch_roles = ['member', 'account_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


class AccountAdminRevokedNotification(
    DocumentIsAccount,
    Notification[Account, AccountMembership],
    type='account_admin_revoked',
    shadows=AccountAdminNotification,
):
    """Notification of admin membership being revoked."""

    # Notify the affected individual and all account admins
    dispatch_roles = ['member', 'account_admin']
    exclude_actor = True  # Alerts other users of actor's actions; too noisy for actor


# MARK: Site administrator notifications -----------------------------------------------


class CommentReportReceivedNotification(
    Notification[Comment, CommentModeratorReport], type='comment_report_received'
):
    """Notification for comment moderators when a comment is reported as spam."""

    category = notification_categories.site_admin
    title = __("When a comment is reported as spam")

    dispatch_roles = ['comment_moderator']
