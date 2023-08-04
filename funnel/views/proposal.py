"""Views for proposals (submissions)."""

from __future__ import annotations

from typing import Optional, Union

from flask import abort, flash, request

from baseframe import _, __
from baseframe.forms import Form, render_delete_sqla, render_form, render_template
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
    ProposalFeaturedForm,
    ProposalForm,
    ProposalLabelsAdminForm,
    ProposalMemberForm,
    ProposalMoveForm,
    ProposalTransitionForm,
    SavedProjectForm,
)
from ..models import (
    Account,
    Project,
    Proposal,
    ProposalMembership,
    ProposalReceivedNotification,
    ProposalSubmittedNotification,
    ProposalSuuidRedirect,
    db,
    sa,
)
from ..typing import ReturnRenderWith, ReturnView
from .helpers import html_in_json, render_redirect
from .login_session import requires_login, requires_sudo, requires_user_not_spammy
from .mixins import AccountCheckMixin, ProjectViewMixin
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
@route('/<account>/<project>')
class ProjectProposalView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    """Views for proposal management (new/reorder)."""

    @route('sub/new', methods=['GET', 'POST'])
    @route('proposals/new', methods=['GET', 'POST'])
    @requires_login
    @render_with('submission_form.html.jinja2')
    @requires_roles({'reader'})
    @requires_user_not_spammy()
    def new_proposal(self) -> ReturnRenderWith:
        # This along with the `reader` role makes it possible for
        # anyone to submit a proposal if the CFP is open.
        if not self.obj.cfp_state.OPEN and not self.obj.current_roles.editor:
            flash(_("This project is not accepting submissions"), 'error')
            return render_redirect(self.obj.url_for())

        form = ProposalForm(model=Proposal, parent=self.obj)
        if form.validate_on_submit():
            proposal = Proposal(created_by=current_auth.user, project=self.obj)
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
            return render_redirect(proposal.url_for())

        return {
            'title': _("New submission"),
            'form': form,
            'project': self.obj,
            'proposal': None,
            'ref_id': 'form-submission',
        }

    @route('sub/reorder', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    @requestform('target', 'other', ('before', getbool))
    def reorder_proposals(self, target: str, other: str, before: bool) -> ReturnView:
        if Form().validate_on_submit():
            proposal: Proposal = (
                Proposal.query.filter_by(uuid_b58=target)
                .options(sa.orm.load_only(Proposal.id, Proposal.seq))
                .one_or_404()
            )
            other_proposal: Proposal = (
                Proposal.query.filter_by(uuid_b58=other)
                .options(sa.orm.load_only(Proposal.id, Proposal.seq))
                .one_or_404()
            )
            proposal.current_access().reorder_item(other_proposal, before)
            db.session.commit()
            return {'status': 'ok'}
        return {'status': 'error', 'error': 'csrf'}, 422


ProjectProposalView.init_app(app)


@Proposal.views('main')
@route('/<account>/<project>/proposals/<proposal>')
@route('/<account>/<project>/sub/<proposal>')
class ProposalView(AccountCheckMixin, UrlChangeCheck, UrlForView, ModelView):
    model = Proposal
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'proposal': 'url_name_uuid_b58',
    }
    obj: Union[Proposal, ProposalSuuidRedirect]

    SavedProjectForm = SavedProjectForm

    def loader(
        self,
        account: str,  # skipcq: PYL-W0613
        project: str,  # skipcq: PYL-W0613
        proposal: str,
    ) -> Union[Proposal, ProposalSuuidRedirect]:
        # `account` and `project` are part of the URL, but unnecessary for loading
        # a proposal since it has a unique id embedded. These parameters are not
        # used in the query.
        obj = (
            self.model.query.join(Project)
            .join(Account, Project.account)
            .filter(Proposal.url_name_uuid_b58 == proposal)
            .first()
        )
        if obj is None:
            if request.method == 'GET':
                return (
                    ProposalSuuidRedirect.query.join(Proposal)
                    .filter(ProposalSuuidRedirect.suuid == proposal.split('-')[-1])
                    .first_or_404()
                )
            abort(404)

        if obj.project.state.DELETED or obj.state.DELETED:
            abort(410)
        return obj

    def after_loader(self) -> Optional[ReturnView]:
        if isinstance(self.obj, ProposalSuuidRedirect):
            if self.obj.proposal:
                self.account = self.obj.proposal.project.account
                return render_redirect(
                    self.obj.proposal.url_for(),
                    302 if request.method == 'GET' else 303,
                )
            abort(410)
        self.account = self.obj.project.account
        return super().after_loader()

    @route('')
    @render_with(html_in_json('submission.html.jinja2'))
    @requires_roles({'reader'})
    def view(self) -> ReturnRenderWith:
        return {
            'project': self.obj.project,
            'proposal': self.obj,
            'subscribed': self.obj.commentset.current_roles.document_subscriber,
        }

    @route('admin')
    @render_with('submission_admin_panel.html.jinja2')
    @requires_roles({'project_editor'})
    def admin(self) -> ReturnRenderWith:
        transition_form = ProposalTransitionForm(obj=self.obj)

        proposal_move_form = None
        if 'move_to' in self.obj.current_access():
            proposal_move_form = ProposalMoveForm(user=current_auth.user)

        proposal_label_admin_form = ProposalLabelsAdminForm(
            model=Proposal, obj=self.obj, parent=self.obj.project
        )

        return {
            'proposal': self.obj,
            'project': self.obj.project,
            'transition_form': transition_form,
            'proposal_move_form': proposal_move_form,
            'proposal_label_admin_form': proposal_label_admin_form,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    @render_with('submission_form.html.jinja2')
    def edit(self) -> ReturnRenderWith:
        form = ProposalForm(obj=self.obj, model=Proposal, parent=self.obj.project)
        if form.validate_on_submit():
            with db.session.no_autoflush:
                form.populate_obj(self.obj)
            self.obj.name = make_name(self.obj.title)
            self.obj.update_description()
            self.obj.edited_at = sa.func.utcnow()
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.url_for())
        return {
            'title': _("Edit submission"),
            'form': form,
            'project': self.obj.project,
            'proposal': self.obj,
            'message': markdown_message,
            'ref_id': 'form-submission',
        }

    @route('collaborator/new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def add_collaborator(self) -> ReturnView:
        collaborator_form = ProposalMemberForm(proposal=self.obj)
        if request.method == 'POST':
            if collaborator_form.validate_on_submit():
                with db.session.no_autoflush:
                    membership = ProposalMembership(
                        proposal=self.obj, granted_by=current_auth.user
                    )
                    collaborator_form.populate_obj(membership)
                    db.session.add(membership)
                db.session.commit()
                return {
                    'status': 'ok',
                    'message': _("{user} has been added as an collaborator").format(
                        user=membership.member.pickername
                    ),
                    'html': render_template(
                        'collaborator_list.html.jinja2',
                        collaborators=[
                            _m.current_access(datasets=['primary', 'related'])
                            for _m in self.obj.memberships
                        ],
                    ),
                }, 201
            return (
                {
                    'status': 'error',
                    'error_description': _("Pick a user to be added"),
                    'errors': collaborator_form.errors,
                    'form_nonce': collaborator_form.form_nonce.data,
                },
                400,
            )
        return render_form(
            form=collaborator_form,
            title='',
            submit='Add collaborator',
            ajax=True,
            with_chrome=True,
            template='modalajaxform.html.jinja2',
        )

    @route('collaborator/reorder', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    @requestform('target', 'other', ('before', getbool))
    def reorder_collaborators(
        self, target: str, other: str, before: bool
    ) -> ReturnView:
        if Form().validate_on_submit():
            target_membership = ProposalMembership.query.filter_by(
                uuid_b58=target, proposal=self.obj
            ).one_or_404()
            other_membership = ProposalMembership.query.filter_by(
                uuid_b58=other, proposal=self.obj
            ).one_or_404()
            target_membership.current_access().reorder_item(other_membership, before)
            db.session.commit()
            return {'status': 'ok'}
        return {'status': 'error', 'error': 'csrf'}, 422

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'editor', 'project_editor'})
    def delete(self) -> ReturnView:
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
    def transition(self) -> ReturnView:
        transition_form = ProposalTransitionForm(obj=self.obj)
        # check if the provided transition is valid
        if transition_form.validate_on_submit():
            transition = getattr(
                self.obj.current_access(), transition_form.transition.data
            )
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')

            if transition_form.transition.data == 'delete':
                # if the proposal is deleted, don't redirect to proposal page
                return render_redirect(self.obj.project.url_for('view_proposals'))
        else:
            flash(_("Invalid transition for this submission"), 'error')
            abort(403)
        return render_redirect(self.obj.url_for())

    @route('move', methods=['POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def moveto(self) -> ReturnView:
        proposal_move_form = ProposalMoveForm(user=current_auth.user)
        if proposal_move_form.validate_on_submit():
            target_project = proposal_move_form.target.data
            if target_project != self.obj.project:
                self.obj.current_access().move_to(target_project)
                db.session.commit()
            flash(
                _("This submission has been moved to {project}").format(
                    project=target_project.title
                ),
                'success',
            )
        else:
            flash(
                _("Please choose the project you want to move this submission to"),
                'error',
            )
        return render_redirect(self.obj.url_for())

    @route('update_featured', methods=['POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def update_featured(self) -> ReturnView:
        featured_form = ProposalFeaturedForm(obj=self.obj)
        if featured_form.validate_on_submit():
            featured_form.populate_obj(self.obj)
            db.session.commit()
            if self.obj.featured:
                return {
                    'status': 'ok',
                    'message': _("This submission has been featured"),
                }
            return {
                'status': 'ok',
                'message': _("This submission is no longer featured"),
            }
        return (
            {'status': 'error', 'error': 'validation', 'errors': featured_form.errors},
            422,
        )

    @route('schedule', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def schedule(self) -> ReturnView:
        return session_edit(self.obj.project, proposal=self.obj)

    @route('labels', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def edit_labels(self) -> ReturnView:
        form = ProposalLabelsAdminForm(
            model=Proposal, obj=self.obj, parent=self.obj.project
        )
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Labels have been saved for this submission"), 'info')
            return render_redirect(self.obj.url_for())
        flash(_("Labels could not be saved for this submission"), 'error')
        return render_form(
            form,
            submit=_("Save changes"),
            title=_("Edit labels for '{}'").format(self.obj.title),
        )

    @route('contacts.json', methods=['GET'])
    @requires_login
    @requires_roles({'project_editor'})
    def contacts_json(self):
        """Return the contact details of collaborators as JSON."""
        return {
            'title': self.obj.title,
            'collaborators': [
                {
                    'fullname': membership.subject.fullname,
                    'username': membership.subject.username,
                    'profile': membership.subject.profile_url,
                    'email': str(membership.subject.email),
                    'phone': str(membership.subject.phone),
                }
                for membership in self.obj.memberships
            ],
        }


ProposalView.init_app(app)


@ProposalMembership.views('main')
@route('/<account>/<project>/sub/<proposal>/collaborator/<membership>')
class ProposalMembershipView(AccountCheckMixin, UrlChangeCheck, UrlForView, ModelView):
    model = ProposalMembership
    route_model_map = {
        'account': 'proposal.project.account.urlname',
        'project': 'proposal.project.name',
        'proposal': 'proposal.url_name_uuid_b58',
        'membership': 'uuid_b58',
    }
    obj: ProposalMembership

    def loader(
        self,
        account: str,  # skipcq: PYL-W0613
        project: str,  # skipcq: PYL-W0613
        proposal: str,  # skipcq: PYL-W0613
        membership: str,
    ) -> ProposalMembership:
        # `account`, `project` and `proposal` are part of the URL, but unnecessary for
        # loading a proposal membership since it has a unique id.
        obj = self.model.query.filter(
            ProposalMembership.uuid_b58 == membership
        ).one_or_404()
        if obj.revoked_at is not None:
            abort(410)
        return obj

    def after_loader(self):
        self.account = self.obj.proposal.project.account
        return super().after_loader()

    def collaborators(self):
        return [
            _m.current_access(datasets=['primary', 'related'])
            for _m in self.obj.proposal.memberships
        ]

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def edit(self) -> ReturnView:
        membership = self.obj.current_access()
        collaborator_form = ProposalMemberForm(
            proposal=self.obj.proposal, obj=membership
        )
        del collaborator_form.user
        if collaborator_form.validate_on_submit():
            with db.session.no_autoflush, membership.amend_by(
                current_auth.user
            ) as amendment:
                collaborator_form.populate_obj(amendment)
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("{user}’s role has been updated").format(
                    user=membership.member.pickername
                )
                if amendment.membership is not self.obj
                else None,
                'html': render_template(
                    'collaborator_list.html.jinja2',
                    collaborators=self.collaborators(),
                ),
            }
        return render_form(
            form=collaborator_form,
            title='',
            submit='Save',
            ajax=True,
            with_chrome=True,
            template='modalajaxform.html.jinja2',
        )

    @route('remove', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    def remove(self) -> ReturnView:
        membership = self.obj.current_access()
        if Form().validate_on_submit():
            if len(self.obj.proposal.memberships) == 1:
                # Can't remove last member
                return {
                    'status': 'error',
                    'error': 'last_collaborator',
                    'message': _(
                        "The sole collaborator on a submission cannot be removed"
                    ),
                }, 422
            membership.revoke(actor=current_auth.user)
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("{user} is no longer a collaborator").format(
                    user=membership.member.pickername
                ),
                'html': render_template(
                    'collaborator_list.html.jinja2', collaborators=self.collaborators()
                ),
            }
        return {'status': 'error', 'error': 'csrf'}, 422


ProposalMembershipView.init_app(app)
