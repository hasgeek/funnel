from flask import Markup, abort, escape, flash, jsonify, redirect

from bleach import linkify

from baseframe import _, __, forms, request_is_xhr
from baseframe.forms import render_delete_sqla, render_form
from coaster.auth import current_auth
from coaster.utils import make_name
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    jsonp,
    render_with,
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

proposal_headers = [
    'id',
    'title',
    'url',
    'fullname',
    'proposer',
    'speaker',
    'email',
    'slides',
    'video_url',
    'phone',
    'type',
    'level',
    'votes',
    'comments',
    'submitted',
    'confirmed',
]


markdown_message = __(
    'This form uses <a target="_blank" rel="noopener noreferrer"'
    ' href="https://www.markdownguide.org/basic-syntax/">Markdown</a> for formatting.'
)


def proposal_data(proposal):
    """
    Return proposal data suitable for a JSON dump.

    Request helper, not to be used standalone.
    """
    return dict(
        [
            ('id', proposal.uuid_b58),
            ('name', proposal.url_name_uuid_b58),
            ('legacy_id', proposal.url_id),
            ('legacy_name', proposal.url_name),
            ('title', proposal.title),
            ('url', proposal.url_for(_external=True)),
            ('json_url', proposal.url_for('json', _external=True)),
            ('fullname', proposal.owner.fullname),
            ('proposer', proposal.user.pickername),
            ('speaker', proposal.speaker.pickername if proposal.speaker else None),
            ('description', proposal.description),
            ('body', proposal.body.html),
            ('video', proposal.video),
            ('votes', proposal.voteset.count),
            ('comments', proposal.commentset.count),
            ('submitted', proposal.created_at.isoformat()),
            ('confirmed', bool(proposal.state.CONFIRMED)),
        ]
        + (
            [
                ('email', proposal.email),
                ('phone', proposal.phone),
                ('location', proposal.location),
                ('votes_count', proposal.votes_count()),
                ('status', proposal.state.value),
                ('state', proposal.state.label.name),
            ]
            if proposal.current_roles.project_editor
            else []
        )
    )


def proposal_data_flat(proposal):
    data = proposal_data(proposal)
    cols = [data.get(header) for header in proposal_headers]
    cols.append(proposal.state.label.name)
    return cols


@Proposal.features('comment_new')
def proposal_comment_new(obj):
    return obj.current_roles.commenter is True


# --- Routes ------------------------------------------------------------------
class BaseProjectProposalView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @requires_login
    @requires_roles({'reader'})
    def new_proposal(self):
        # This along with the `reader` role makes it possible for
        # anyone to submit a proposal if the CFP is open.
        if not self.obj.cfp_state.OPEN:
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
            flash(_("Your proposal has been submitted"), 'info')
            dispatch_notification(
                ProposalSubmittedNotification(document=proposal),
                ProposalReceivedNotification(
                    document=proposal.project, fragment=proposal
                ),
            )
            return redirect(proposal.url_for(), code=303)

        return render_form(
            form=form,
            title=_("Submit a proposal"),
            submit=_("Submit"),
            message=markdown_message,
        )


@Project.views('proposal_new')
@route('/<profile>/<project>')
class ProjectProposalView(BaseProjectProposalView):
    pass


ProjectProposalView.add_route_for(
    'new_proposal', 'proposals/new', methods=['GET', 'POST']
)
ProjectProposalView.init_app(app)


@route('/<project>', subdomain='<profile>')
class FunnelProjectProposalView(BaseProjectProposalView):
    pass


FunnelProjectProposalView.add_route_for('new_proposal', 'new', methods=['GET', 'POST'])
FunnelProjectProposalView.init_app(funnelapp)


@Proposal.views('main')
@route('/<profile>/<project>/proposals/<url_name_uuid_b58>')
class ProposalView(ProposalViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('proposal.html.jinja2')
    @requires_permission('view')
    def view(self):
        # FIXME: Use a separate endpoint for comments as this is messing with browser
        # cache. View Source on proposal pages shows comments tree instead of source
        if request_is_xhr():
            return jsonify({'comments': self.obj.commentset.views.json_comments()})

        links = [
            Markup(linkify(str(escape(link))))
            for link in self.obj.links.replace('\r\n', '\n').split('\n')
            if link
        ]

        return {
            'project': self.obj.project,
            'proposal': self.obj,
            'links': links,
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

    @route('json')
    @requires_permission('view')
    def json(self):
        return jsonp(proposal_data(self.obj))

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
            title=_("Edit proposal"),
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
                "Delete your proposal ‘{title}’? This will remove all votes and"
                " comments as well. This operation is permanent and cannot be undone."
            ).format(title=self.obj.title),
            success=_("Your proposal has been deleted"),
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
            flash(_("Invalid transition for this proposal."), 'error')
            abort(403)
        return redirect(self.obj.url_for())

    @route('next')  # NOQA: A003
    @requires_permission('view')
    def next(self):  # NOQA: A003
        nextobj = self.obj.getnext()
        if nextobj:
            return redirect(nextobj.url_for())
        else:
            flash(_("You were at the last proposal"), 'info')
            return redirect(self.obj.project.url_for())

    @route('prev')
    @requires_permission('view')
    def prev(self):
        prevobj = self.obj.getprev()
        if prevobj:
            return redirect(prevobj.url_for())
        else:
            flash(_("You were at the first proposal"), 'info')
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
                    "This proposal has been moved to {project}.".format(
                        project=target_project.title
                    )
                ),
                'success',
            )
        else:
            flash(
                _("Please choose the project you want to move this proposal to."),
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
            flash(_("This proposal has been transfered."), 'success')
        else:
            flash(
                _("Please choose the user you want to transfer this proposal to."),
                'error',
            )
        return redirect(self.obj.url_for(), 303)

    @route('toggle_featured', methods=['POST'])
    @requires_login
    @requires_permission('move-proposal')
    def toggle_featured(self):
        featured_form = forms.Form()
        if featured_form.validate_on_submit():
            self.obj.featured = not self.obj.featured
            db.session.commit()
        return redirect(self.obj.url_for(), 303)

    @route('schedule', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('new-session')
    def schedule(self):
        from .session import session_form

        return session_form(self.obj.project, proposal=self.obj)

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
            flash(_("Labels have been saved for this proposal."), 'info')
            return redirect(self.obj.url_for(), 303)
        else:
            flash(_("Labels could not be saved for this proposal."), 'error')
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
