from __future__ import annotations

from flask import abort, flash, redirect

from baseframe import _, __
from baseframe.forms import Form, render_delete_sqla, render_form
from coaster.auth import current_auth
from coaster.utils import getbool, make_name
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requestform,
    requires_roles,
    route,
)

from .. import app
from ..forms import (
    ProposalForm,
    ProposalLabelsAdminForm,
    ProposalMemberForm,
    ProposalMoveForm,
    ProposalTransferForm,
    ProposalTransitionForm,
    SavedProjectForm,
)
from ..models import (
    Project,
    Proposal,
    ProposalMembership,
    ProposalReceivedNotification,
    ProposalSubmittedNotification,
    ReplaceMembership,
    db,
)
from .login_session import requires_login, requires_sudo
from .mixins import ProjectViewMixin, ProposalViewMixin
from .notification import dispatch_notification
from .session import session_edit

markdown_message = __(
    'This form uses <a target="_blank" rel="noopener noreferrer"'
    ' href="https://www.markdownguide.org/basic-syntax/">Markdown</a> for formatting'
)


@Proposal.features('comment_new')
def proposal_comment_new(obj):
    return obj.current_roles.commenter


@Project.features('reorder_proposals')
def proposals_can_be_reordered(obj):
    return obj.current_roles.editor


# --- Routes ------------------------------------------------------------------
@Project.views('proposal_new')
@route('/<profile>/<project>')
class ProjectProposalView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    """Views for proposal management (new/reorder)."""

    @route('sub/new', methods=['GET', 'POST'])
    @route('proposals/new', methods=['GET', 'POST'])
    @requires_login
    @render_with('submission_form.html.jinja2')
    @requires_roles({'reader'})
    def new_proposal(self):
        # This along with the `reader` role makes it possible for
        # anyone to submit a proposal if the CFP is open.
        if not self.obj.cfp_state.OPEN and not self.obj.current_roles.editor:
            flash(_("This project is not accepting submissions"), 'error')
            return redirect(self.obj.url_for(), code=303)

        form = ProposalForm(model=Proposal, parent=self.obj)
        proposal: Proposal = None

        if form.validate_on_submit():
            proposal = Proposal(user=current_auth.user, project=self.obj)
            db.session.add(proposal)
            with db.session.no_autoflush:
                form.populate_obj(proposal)
            proposal.name = make_name(proposal.title)
            proposal.update_description()
            db.session.commit()
            dispatch_notification(
                ProposalSubmittedNotification(document=proposal),
                ProposalReceivedNotification(
                    document=proposal.project, fragment=proposal
                ),
            )
            return redirect(proposal.url_for(), code=303)

        return {
            'title': _("New submission"),
            'form': form,
            'project': self.obj,
            'proposal': proposal,
            'ref_id': 'form-submission',
        }

    @route('sub/reorder', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    @requestform('target', 'other', ('before', getbool))
    def reorder_proposals(self, target: str, other: str, before: bool):
        if Form().validate_on_submit():
            proposal: Proposal = (
                Proposal.query.filter_by(uuid_b58=target)
                .options(db.load_only(Proposal.id, Proposal.seq))
                .one_or_404()
            )
            other_proposal: Proposal = (
                Proposal.query.filter_by(uuid_b58=other)
                .options(db.load_only(Proposal.id, Proposal.seq))
                .one_or_404()
            )
            proposal.current_access().reorder_item(other_proposal, before)
            db.session.commit()
            return {'status': 'ok'}
        return {'status': 'error'}, 422


ProjectProposalView.init_app(app)


@Proposal.views('main')
@route('/<profile>/<project>/proposals/<proposal>')
@route('/<profile>/<project>/sub/<proposal>')
class ProposalView(ProposalViewMixin, UrlChangeCheck, UrlForView, ModelView):
    SavedProjectForm = SavedProjectForm

    @route('')
    @render_with('submission.html.jinja2')
    @requires_roles({'reader'})
    def view(self):
        return {
            'project': self.obj.project,
            'proposal': self.obj,
            'subscribed': self.obj.commentset.current_roles.document_subscriber,
        }

    @route('admin')
    @render_with('submission_admin_panel.html.jinja2')
    @requires_roles({'project_editor'})
    def admin(self):
        transition_form = ProposalTransitionForm(obj=self.obj)
        proposal_transfer_form = ProposalTransferForm()

        proposal_move_form = None
        if 'move_to' in self.obj.current_access():
            proposal_move_form = ProposalMoveForm()

        proposal_label_admin_form = ProposalLabelsAdminForm(
            model=Proposal, obj=self.obj, parent=self.obj.project
        )

        return {
            'proposal': self.obj,
            'project': self.obj.project,
            'transition_form': transition_form,
            'proposal_move_form': proposal_move_form,
            'proposal_transfer_form': proposal_transfer_form,
            'proposal_label_admin_form': proposal_label_admin_form,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    @render_with('submission_form.html.jinja2')
    def edit(self):
        form = ProposalForm(obj=self.obj, model=Proposal, parent=self.obj.project)
        if form.validate_on_submit():
            with db.session.no_autoflush:
                form.populate_obj(self.obj)
            self.obj.name = make_name(self.obj.title)
            self.obj.update_description()
            self.obj.edited_at = db.func.utcnow()
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for(), code=303)
        return {
            'title': _("Edit submission"),
            'form': form,
            'project': self.obj.project,
            'proposal': self.obj,
            'message': markdown_message,
            'ref_id': 'form-submission',
        }

    @route('add_collaborator', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def add_collaborator(self):
        collaborator_form = ProposalMemberForm(proposal=self.obj)
        if collaborator_form.validate_on_submit():
            with db.session.no_autoflush:
                membership = ProposalMembership(
                    proposal=self.obj, actor=current_auth.user
                )
                collaborator_form.populate_obj(membership)
                db.session.add(membership)
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("{user} has been added as an collaborator").format(
                    user=membership.user.pickername
                ),
                'collaborators': [_m.current_access() for _m in self.obj.memberships],
            }
        return render_form(
            form=collaborator_form,
            title='',
            submit='Add collaborator',
            ajax=True,
            with_chrome=True,
        )

    @route('edit_collaborator/<membership>', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def edit_collaborator(self, membership: str):
        obj = ProposalMembership.query.filter_by(
            proposal=self.obj,
            uuid_b58=membership,
        ).one_or_404()
        if not obj.is_active:
            abort(410)
        replacement = ReplaceMembership(obj)
        collaborator_form = ProposalMemberForm(proposal=self.obj, obj=replacement)
        del collaborator_form.user
        if collaborator_form.validate_on_submit():
            with db.session.no_autoflush:
                collaborator_form.populate_obj(replacement)
                db.session.add(replacement.finalize(current_auth.user))
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("{user}’s role has been updated").format(
                    user=obj.user.pickername
                ),
                'collaborators': [_m.current_access() for _m in self.obj.memberships],
            }
        return render_form(
            form=collaborator_form,
            title='',
            submit='Edit collaborator',
            ajax=True,
            with_chrome=True,
        )

    @route('remove_collaborator/<membership>', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    def remove_collaborator(self, membership: str):
        obj = ProposalMembership.query.filter_by(
            proposal=self.obj, uuid_b58=membership
        ).one_or_404()
        if not obj.is_active:
            abort(410)
        if Form().validate_on_submit():
            obj.revoke(actor=current_auth.user)
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("{user} is no longer a collaborator").format(
                    user=obj.user.pickername
                ),
                'collaborators': [_m.current_access() for _m in self.obj.memberships],
            }
        return {'status': 'error', 'error': 'csrf'}, 422

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'editor', 'project_editor'})
    def delete(self):
        # FIXME: Prevent deletion of confirmed proposals
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete your submission ‘{title}’? This will remove all comments as"
                " well. This operation is permanent and cannot be undone"
            ).format(title=self.obj.title),
            success=_("Your submission has been deleted"),
            next=self.obj.project.url_for(),
            cancel_url=self.obj.url_for(),
        )

    @route('transition', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def transition(self):
        transition_form = ProposalTransitionForm(obj=self.obj)
        if (
            transition_form.validate_on_submit()
        ):  # check if the provided transition is valid
            transition = getattr(
                self.obj.current_access(), transition_form.transition.data
            )
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')

            if transition_form.transition.data == 'delete':
                # if the proposal is deleted, don't redirect to proposal page
                return redirect(self.obj.project.url_for('view_proposals'))
        else:
            flash(_("Invalid transition for this submission"), 'error')
            abort(403)
        return redirect(self.obj.url_for())

    @route('move', methods=['POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def moveto(self):
        proposal_move_form = ProposalMoveForm()
        if proposal_move_form.validate_on_submit():
            target_project = proposal_move_form.target.data
            if target_project != self.obj.project:
                self.obj.current_access().move_to(target_project)
                db.session.commit()
            flash(
                _(
                    "This submission has been moved to {project}".format(
                        project=target_project.title
                    )
                ),
                'success',
            )
        else:
            flash(
                _("Please choose the project you want to move this submission to"),
                'error',
            )
        return redirect(self.obj.url_for(), 303)

    @route('transfer', methods=['POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def transfer_to(self):
        proposal_transfer_form = ProposalTransferForm()
        if proposal_transfer_form.validate_on_submit():
            target_user = proposal_transfer_form.user.data
            self.obj.current_access().transfer_to(
                [target_user], actor=current_auth.actor
            )
            db.session.commit()
            flash(_("This submission has been transferred"), 'success')
        else:
            flash(
                _("Please choose the user you want to transfer this submission to"),
                'error',
            )
        return redirect(self.obj.url_for(), 303)

    @route('update_featured', methods=['POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def update_featured(self):
        featured_form = self.obj.forms.featured()
        if featured_form.validate_on_submit():
            featured_form.populate_obj(self.obj)
            db.session.commit()
            if self.obj.featured:
                return {'status': 'ok', 'message': 'This submission has been featured'}
            else:
                return {
                    'status': 'ok',
                    'message': 'This submission is no longer featured',
                }
        return (
            {
                'status': 'error',
                'error_description': featured_form.errors,
            },
            422,
        )

    @route('schedule', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def schedule(self):
        return session_edit(self.obj.project, proposal=self.obj)

    @route('labels', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def edit_labels(self):
        form = ProposalLabelsAdminForm(
            model=Proposal, obj=self.obj, parent=self.obj.project
        )
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Labels have been saved for this submission"), 'info')
            return redirect(self.obj.url_for(), 303)
        else:
            flash(_("Labels could not be saved for this submission"), 'error')
            return render_form(
                form,
                submit=_("Save changes"),
                title=_("Edit labels for '{}'").format(self.obj.title),
            )


ProposalView.init_app(app)
