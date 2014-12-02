# -*- coding: utf-8 -*-

from coaster.docflow import DocumentWorkflow, WorkflowState, WorkflowStateGroup, InteractiveTransition
from baseframe import __
from ..models import PROPOSALSTATUS, User, Proposal
from ..forms import TransferProposal

__all__ = ['ProposalWorkflow']


# class PROPOSALSTATUS(LabeledEnum):
#     # Draft-state for future use, so people can save their proposals and submit only when ready
#     DRAFT = (0, __("Draft"))
#     SUBMITTED = (1, __("Submitted"))
#     CONFIRMED = (2, __("Confirmed"))
#     WAITLISTED = (3, __("Waitlisted"))
#     SHORTLISTED = (4, __("Shortlisted"))
#     REJECTED = (5, __("Rejected"))
#     CANCELLED = (6, __("Cancelled"))


class ProposalWorkflow(DocumentWorkflow):
    """
    Workflow for proposal spaces.
    """

    state_attr = 'status'

    draft = WorkflowState(PROPOSALSTATUS.DRAFT, title=__(u"Draft"))
    submitted = WorkflowState(PROPOSALSTATUS.SUBMITTED, title=__(u"Submitted"))
    confirmed = WorkflowState(PROPOSALSTATUS.CONFIRMED, title=__(u"Confirmed"))
    waitlisted = WorkflowState(PROPOSALSTATUS.WAITLISTED, title=__(u"Waitlisted"))
    shortlisted = WorkflowState(PROPOSALSTATUS.SHORTLISTED, title=__(u"Shortlisted"))
    rejected = WorkflowState(PROPOSALSTATUS.REJECTED, title=__(u"Rejected"))
    cancelled = WorkflowState(PROPOSALSTATUS.CANCELLED, title=__(u"Cancelled"))

    visible = WorkflowStateGroup([submitted, confirmed, waitlisted, shortlisted, rejected, cancelled], title=__(u"Visible"))
    unconfirmed = WorkflowStateGroup([submitted, waitlisted, shortlisted, rejected], title=__(u"Unconfirmed"))

    # Owner's transitions
    @draft.transition(submitted, 'edit-proposal', title=__(u"Submit"))
    def submit(self):
        pass

    # Owner/reviewer's transitions
    @draft.transition(draft, 'edit-proposal', name=u'transfer', title=__(u"Transfer"))
    @submitted.transition(submitted, 'edit-proposal', name=u'transfer', title=__(u"Transfer"))
    @confirmed.transition(confirmed, 'confirm-proposal', name=u'transfer', title=__(u"Transfer"))
    @waitlisted.transition(waitlisted, 'confirm-proposal', name=u'transfer', title=__(u"Transfer"))
    @shortlisted.transition(shortlisted, 'confirm-proposal', name=u'transfer', title=__(u"Transfer"))
    class Transfer(InteractiveTransition):
        formclass = TransferProposal

        def submit(self):
            user = User.get(self.form.userid.data)
            if user:
                self.document.speaker = user

    # Reviewer's transitions
    @submitted.transition(draft, 'edit-proposal', title=__(u"Withdraw"))
    def withdraw(self):
        pass

    @submitted.transition(shortlisted, 'confirm-proposal', title=__(u"Shortlist"))
    def shortlist(self):
        pass

    @confirmed.transition_from([submitted, waitlisted, shortlisted],
        'confirm-proposal', title=__(u"Confirm"))
    def confirm(self):
        pass

    @waitlisted.transition_from([submitted, confirmed, shortlisted, rejected, cancelled],
        'confirm-proposal', title=__(u"Waitlist"))
    def waitlist(self):
        pass

    @submitted.transition(rejected, 'confirm-proposal', title=__(u"Reject"))
    def reject(self):
        pass

    @confirmed.transition(submitted, 'confirm-proposal', title=__(u"Cancel confirmation"))
    def unconfirm(self):
        pass


ProposalWorkflow.apply_on(Proposal)
