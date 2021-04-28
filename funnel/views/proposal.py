from flask import abort, flash, jsonify, redirect

from baseframe import _, __, request_is_xhr
from baseframe.forms import Form, render_delete_sqla, render_form
from coaster.auth import current_auth
from coaster.utils import getbool, make_name
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requestform,
    requires_permission,
    requires_roles,
    route,
)

from .. import app, funnelapp
from ..forms import (
    ProposalForm,
    ProposalLabelsAdminForm,
    ProposalMoveForm,
    ProposalTransferForm,
    ProposalTransitionForm,
    SavedProjectForm,
)
from ..models import (
    Project,
    Proposal,
    ProposalReceivedNotification,
    ProposalSubmittedNotification,
    db,
)
from .decorators import legacy_redirect
from .login_session import requires_login, requires_sudo
from .mixins import ProjectViewMixin, ProposalViewMixin
from .notification import dispatch_notification
from .session import session_edit

markdown_message = __(
    'This form uses <a target="_blank" rel="noopener noreferrer"'
    ' href="https://www.markdownguide.org/basic-syntax/">Markdown</a> for formatting.'
)


@Proposal.features('comment_new')
def proposal_comment_new(obj):
    return obj.current_roles.commenter


@Project.features('reorder_proposals')
def proposals_can_be_reordered(obj):
    return obj.current_roles.editor


# --- Routes ------------------------------------------------------------------
class BaseProjectProposalView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @requires_login
    @requires_roles({'reader'})
    def new_proposal(self):
        # This along with the `reader` role makes it possible for
        # anyone to submit a proposal if the CFP is open.
        if not self.obj.cfp_state.OPEN and not self.obj.current_roles.editor:
            flash(_("This project is not accepting submissions"), 'error')
            return redirect(self.obj.url_for(), code=303)

        form = ProposalForm(model=Proposal, parent=self.obj)

        if form.validate_on_submit():
            proposal = Proposal(
                user=current_auth.user, speaker=current_auth.user, project=self.obj
            )
            db.session.add(proposal)
            with db.session.no_autoflush:
                form.populate_obj(proposal)
            proposal.name = make_name(proposal.title)
            proposal.update_description()
            proposal.voteset.vote(
                current_auth.user
            )  # Vote up your own proposal by default
            db.session.commit()
            flash(_("Your submission has been submitted"), 'info')
            dispatch_notification(
                ProposalSubmittedNotification(document=proposal),
                ProposalReceivedNotification(
                    document=proposal.project, fragment=proposal
                ),
            )
            return redirect(proposal.url_for(), code=303)

        return render_form(
            form=form,
            title=_("Make a submission"),
            submit=_("Submit"),
            message=markdown_message,
        )

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
        return {'status': 'error'}, 400


@Project.views('proposal_new')
@route('/<profile>/<project>')
class ProjectProposalView(BaseProjectProposalView):
    pass


ProjectProposalView.add_route_for(
    'new_proposal', 'proposals/new', methods=['GET', 'POST']
)
ProjectProposalView.add_route_for('new_proposal', 'sub/new', methods=['GET', 'POST'])
ProjectProposalView.add_route_for('reorder_proposals', 'sub/reorder', methods=['POST'])
ProjectProposalView.init_app(app)


@route('/<project>', subdomain='<profile>')
class FunnelProjectProposalView(BaseProjectProposalView):
    pass


FunnelProjectProposalView.add_route_for('new_proposal', 'new', methods=['GET', 'POST'])
FunnelProjectProposalView.init_app(funnelapp)


@Proposal.views('main')
@route('/<profile>/<project>/proposals/<url_name_uuid_b58>')
@route('/<profile>/<project>/sub/<url_name_uuid_b58>')
class ProposalView(ProposalViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]
    SavedProjectForm = SavedProjectForm

    @route('')
    @render_with('proposal.html.jinja2')
    @requires_permission('view')
    def view(self):
        # FIXME: Use a separate endpoint for comments as this is messing with browser
        # cache. View Source on proposal pages shows comments tree instead of source
        if request_is_xhr():
            return jsonify({'comments': self.obj.commentset.views.json_comments()})

        return {
            'project': self.obj.project,
            'proposal': self.obj,
        }

    @route('admin')
    @render_with('proposal_admin_panel.html.jinja2')
    @requires_permission('view')
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

    @route('comments', methods=['GET'])
    @render_with(json=True)
    @requires_roles({'reader'})
    def comments(self):
        if request_is_xhr():
            return {'comments': self.obj.commentset.views.json_comments()}
        else:
            return redirect(self.obj.commentset.views.url(), code=303)

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('edit_proposal')
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
        return render_form(
            form=form,
            title=_("Edit submission"),
            submit=_("Update"),
            message=markdown_message,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_permission('delete-proposal')
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete your submission ‘{title}’? This will remove all votes and"
                " comments as well. This operation is permanent and cannot be undone."
            ).format(title=self.obj.title),
            success=_("Your submission has been deleted"),
            next=self.obj.project.url_for(),
            cancel_url=self.obj.url_for(),
        )

    @route('transition', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('confirm-proposal')
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
            flash(_("Invalid transition for this submission."), 'error')
            abort(403)
        return redirect(self.obj.url_for())

    @route('next')  # NOQA: A003
    @requires_permission('view')
    def next(self):  # NOQA: A003
        nextobj = self.obj.getnext()
        if nextobj:
            return redirect(nextobj.url_for())
        else:
            flash(_("You were at the last submission"), 'info')
            return redirect(self.obj.project.url_for())

    @route('prev')
    @requires_permission('view')
    def prev(self):
        prevobj = self.obj.getprev()
        if prevobj:
            return redirect(prevobj.url_for())
        else:
            flash(_("You were at the first submission"), 'info')
            return redirect(self.obj.project.url_for())

    @route('move', methods=['POST'])
    @requires_login
    @requires_permission('move-proposal')
    def moveto(self):
        proposal_move_form = ProposalMoveForm()
        if proposal_move_form.validate_on_submit():
            target_project = proposal_move_form.target.data
            if target_project != self.obj.project:
                self.obj.current_access().move_to(target_project)
                db.session.commit()
            flash(
                _(
                    "This submission has been moved to {project}.".format(
                        project=target_project.title
                    )
                ),
                'success',
            )
        else:
            flash(
                _("Please choose the project you want to move this submission to."),
                'error',
            )
        return redirect(self.obj.url_for(), 303)

    @route('transfer', methods=['POST'])
    @requires_login
    @requires_permission('move-proposal')
    def transfer_to(self):
        proposal_transfer_form = ProposalTransferForm()
        if proposal_transfer_form.validate_on_submit():
            target_user = proposal_transfer_form.user.data
            self.obj.current_access().transfer_to(target_user)
            db.session.commit()
            flash(_("This submission has been transferred."), 'success')
        else:
            flash(
                _("Please choose the user you want to transfer this submission to."),
                'error',
            )
        return redirect(self.obj.url_for(), 303)

    @route('update_featured', methods=['POST'])
    @requires_login
    @requires_permission('move-proposal')
    def update_featured(self):
        featured_form = self.obj.forms.featured()
        if featured_form.validate_on_submit():
            featured_form.populate_obj(self.obj)
            db.session.commit()
            if self.obj.featured:
                return {'status': 'ok', 'message': 'This submission has been featured.'}
            else:
                return {
                    'status': 'ok',
                    'message': 'This submission is no longer featured.',
                }
        return (
            {
                'status': 'error',
                'error_description': featured_form.errors,
            },
            400,
        )

    @route('schedule', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('new-session')
    def schedule(self):
        return session_edit(self.obj.project, proposal=self.obj)

    @route('labels', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('admin')
    def edit_labels(self):
        form = ProposalLabelsAdminForm(
            model=Proposal, obj=self.obj, parent=self.obj.project
        )
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Labels have been saved for this submission."), 'info')
            return redirect(self.obj.url_for(), 303)
        else:
            flash(_("Labels could not be saved for this submission."), 'error')
            return render_form(
                form,
                submit=_("Save changes"),
                title=_("Edit labels for '{}'").format(self.obj.title),
            )


@route('/<project>/<url_id_name>', subdomain='<profile>')
class FunnelProposalView(ProposalView):
    pass


ProposalView.init_app(app)
FunnelProposalView.init_app(funnelapp)
