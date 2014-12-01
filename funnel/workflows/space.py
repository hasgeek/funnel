# -*- coding: utf-8 -*-

from coaster.docflow import DocumentWorkflow, WorkflowState
from baseframe import __
from ..models import SPACESTATUS, ProposalSpace

__all__ = ['ProposalSpaceWorkflow']


# class SPACESTATUS:
#     DRAFT = 0
#     SUBMISSIONS = 1
#     VOTING = 2
#     JURY = 3
#     FEEDBACK = 4
#     CLOSED = 5
#     WITHDRAWN = 6

#     {% trans %}Draft{% endtrans %}
#     {% trans %}Accepting submissions{% endtrans %}
#     {% trans %}Accepting votes{% endtrans %}
#     {% trans %}Submissions and voting closed, awaiting jury selection{% endtrans %}
#     {% trans %}Open for post-event feedback{% endtrans %}
#     {% trans %}Closed{% endtrans %}
#     {% trans %}Withdrawn{% endtrans %}


class ProposalSpaceWorkflow(DocumentWorkflow):
    """
    Workflow for proposal spaces.
    """

    state_attr = 'status'

    draft = WorkflowState(SPACESTATUS.DRAFT, title=__(u"Draft"))
    submissions = WorkflowState(SPACESTATUS.SUBMISSIONS, title=__(u"Accepting submissions"))
    voting = WorkflowState(SPACESTATUS.VOTING, title=__(u"Accepting votes"))
    jury = WorkflowState(SPACESTATUS.JURY, title=__(u"Awaiting jury selection"))
    feedback = WorkflowState(SPACESTATUS.FEEDBACK, title=__(u"Open for feedback"))
    closed = WorkflowState(SPACESTATUS.CLOSED, title=__(u"Closed"))
    withdrawn = WorkflowState(SPACESTATUS.WITHDRAWN, title=__(u"Withdrawn"))

    @draft.transition(submissions, 'edit-space', title=__(u"Publish"))
    def publish(self):
        pass

    @submissions.transition(draft, 'edit-space', title=__(u"Unpublish"))
    def unpublish(self):
        pass

    @submissions.transition(voting, 'edit-space', title=__(u"Close submissions"))
    def close_submissions(self):
        pass

    @submissions.transition(closed, 'edit-space', title=__(u"Close event"))
    @voting.transition(closed, 'edit-space', title=__(u"Close event"))
    @jury.transition(closed, 'edit-space', title=__(u"Close event"))
    @feedback.transition(closed, 'edit-space', title=__(u"Close event"))
    def close(self):
        pass

    @voting.transition(submissions, 'edit-space', title=__(u"Re-open event"))
    @jury.transition(submissions, 'edit-space', title=__(u"Re-open event"))
    @feedback.transition(submissions, 'edit-space', title=__(u"Re-open event"))
    @closed.transition(submissions, 'edit-space', title=__(u"Re-open event"))
    def reopen(self):
        pass

ProposalSpaceWorkflow.apply_on(ProposalSpace)
