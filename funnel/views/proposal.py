# -*- coding: utf-8 -*-

from datetime import datetime
from bleach import linkify

from flask import g, redirect, request, Markup, abort, flash, escape
from coaster.utils import make_name
from coaster.views import ModelView, UrlChangeCheck, UrlForView, jsonp, render_with, requires_permission, route
from coaster.auth import current_auth
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla, Form

from .. import app, funnelapp, lastuser
from ..models import db, Proposal, Comment
from ..forms import (ProposalForm, CommentForm, DeleteCommentForm,
    ProposalTransitionForm, ProposalMoveForm, ProposalLabelsForm,
    ProposalLabelsAdminForm)
from .mixins import ProjectViewMixin, ProposalViewMixin
from .decorators import legacy_redirect


proposal_headers = [
    'id',
    'title',
    'url',
    'fullname',
    'proposer',
    'speaker',
    'email',
    'slides',
    'preview_video',
    'phone',
    'section',
    'type',
    'level',
    'votes',
    'comments',
    'submitted',
    'confirmed'
]


def proposal_data(proposal):
    """
    Return proposal data suitable for a JSON dump. Request helper, not to be used standalone.
    """
    return dict(
        [
            ('id', proposal.suuid),
            ('name', proposal.url_name_suuid),
            ('legacy_id', proposal.url_id),
            ('legacy_name', proposal.url_name),
            ('title', proposal.title),
            ('url', proposal.url_for(_external=True)),
            ('json_url', proposal.url_for('json', _external=True)),
            ('fullname', proposal.owner.fullname),
            ('proposer', proposal.user.pickername),
            ('speaker', proposal.speaker.pickername if proposal.speaker else None),
            ('section', proposal.section.title if proposal.section else None),
            ('type', proposal.session_type),
            ('level', proposal.technical_level),
            ('objective', proposal.objective.html),
            ('description', proposal.description.html),
            ('requirements', proposal.requirements.html),
            ('slides', proposal.slides.url),
            ('links', proposal.links),
            ('preview_video', proposal.preview_video.url),
            ('bio', proposal.bio.html),
            ('votes', proposal.voteset.count),
            ('comments', proposal.commentset.count),
            ('submitted', proposal.created_at.isoformat() + 'Z'),
            ('confirmed', bool(proposal.state.CONFIRMED)),
        ] + ([
            ('email', proposal.email),
            ('phone', proposal.phone),
            ('location', proposal.location),
            ('votes_count', proposal.votes_count()),
            ('status', proposal.state.value),
            ('state', proposal.state.label.name),
        ] if current_auth.permissions.view_contactinfo else []))


def proposal_data_flat(proposal):
    data = proposal_data(proposal)
    cols = [data.get(header) for header in proposal_headers]
    cols.append(proposal.state.label.name)
    return cols


# --- Routes ------------------------------------------------------------------
class BaseProjectProposalView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @lastuser.requires_login
    @requires_permission('new-proposal')
    def new_proposal(self):
        form = ProposalForm(model=Proposal, parent=self.obj)
        if request.method == 'GET':
            form.email.data = g.user.email
            form.phone.data = g.user.phone
        if form.validate_on_submit():
            proposal = Proposal(user=current_auth.user, project=self.obj)
            form.populate_obj(proposal)
            proposal.name = make_name(proposal.title)
            db.session.add(proposal)
            proposal.voteset.vote(g.user)  # Vote up your own proposal by default
            db.session.commit()
            flash(_("Your new session has been saved"), 'info')
            return redirect(proposal.url_for(), code=303)
        return render_form(form=form, title=_("Submit a session proposal"),
            submit=_("Submit proposal"),
            message=Markup(
                _('This form uses <a target="_blank" href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.')))


@route('/<profile>/<project>')
class ProjectProposalView(BaseProjectProposalView):
    pass


ProjectProposalView.add_route_for('new_proposal', 'proposals/new', methods=['GET', 'POST'])
ProjectProposalView.init_app(app)


@route('/<project>', subdomain='<profile>')
class FunnelProjectProposalView(BaseProjectProposalView):
    pass


FunnelProjectProposalView.add_route_for('new_proposal', 'new', methods=['GET', 'POST'])
FunnelProjectProposalView.init_app(funnelapp)


@route('/<profile>/<project>/proposals/<url_name_suuid>')
class ProposalView(ProposalViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('proposal.html.jinja2')
    @requires_permission('view')
    def view(self):
        comments = sorted(Comment.query.filter_by(commentset=self.obj.commentset, parent=None).order_by('created_at').all(),
            key=lambda c: c.voteset.count, reverse=True)
        commentform = CommentForm(model=Comment)
        delcommentform = DeleteCommentForm()

        links = [Markup(linkify(unicode(escape(l)))) for l in self.obj.links.replace('\r\n', '\n').split('\n') if l]

        transition_form = ProposalTransitionForm(obj=self.obj)

        proposal_move_form = None
        if 'move_to' in self.obj.current_access():
            proposal_move_form = ProposalMoveForm()

        proposal_label_admin_form = ProposalLabelsAdminForm(model=Proposal, obj=self.obj, parent=self.obj.project)

        return dict(project=self.obj.project, proposal=self.obj,
            comments=comments, commentform=commentform, delcommentform=delcommentform,
            links=links, transition_form=transition_form, proposal_move_form=proposal_move_form,
            part_a=self.obj.project.proposal_part_a.get('title', 'Objective'),
            part_b=self.obj.project.proposal_part_b.get('title', 'Description'), csrf_form=Form(),
            proposal_label_admin_form=proposal_label_admin_form)

    @route('json')
    @requires_permission('view')
    def json(self):
        return jsonp(proposal_data(self.obj))

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit_proposal')
    def edit(self):
        form = ProposalForm(obj=self.obj, model=Proposal, parent=self.obj.project)
        if self.obj.user != g.user:
            del form.speaking
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            self.obj.name = make_name(self.obj.title)
            self.obj.edited_at = datetime.utcnow()
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for(), code=303)
        return render_form(form=form, title=_("Edit session proposal"), submit=_("Save changes"),
            message=Markup(
                _('This form uses <a target="_blank" href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.')))

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('delete-proposal')
    def delete(self):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete your proposal ‘{title}’? "
                    u"This will remove all votes and comments as well. This operation "
                    u"is permanent and cannot be undone.").format(title=self.obj.title),
            success=_("Your proposal has been deleted"),
            next=self.obj.project.url_for(),
            cancel_url=self.obj.url_for())

    @route('transition', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('confirm-proposal')
    def transition(self):
        transition_form = ProposalTransitionForm(obj=self.obj)
        if transition_form.validate_on_submit():  # check if the provided transition is valid
            transition = getattr(self.obj.current_access(), transition_form.transition.data)
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')
        else:
            flash(_("Invalid transition for this proposal."), 'error')
            abort(403)
        return redirect(self.obj.url_for())

    @route('next')
    @requires_permission('view')
    def next(self):
        next = self.obj.getnext()
        if next:
            return redirect(next.url_for())
        else:
            flash(_("You were at the last proposal"), 'info')
            return redirect(self.obj.project.url_for())

    @route('prev')
    @requires_permission('view')
    def prev(self):
        prev = self.obj.getprev()
        if prev:
            return redirect(prev.url_for())
        else:
            flash(_("You were at the first proposal"), 'info')
            return redirect(self.obj.project.url_for())

    @route('move', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('move-proposal')
    def moveto(self):
        proposal_move_form = ProposalMoveForm()
        if proposal_move_form.validate_on_submit():
            target_project = proposal_move_form.target.data
            if target_project != self.obj.project:
                self.obj.current_access().move_to(target_project)
                db.session.commit()
            flash(_("This proposal has been moved to {project}.".format(project=target_project.title)))
        else:
            flash(_("Please choose the project you want to move this proposal to."))
        return redirect(self.obj.url_for(), 303)

    @route('schedule', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-session')
    def schedule(self):
        from .session import session_form
        return session_form(self.obj.project, proposal=self.obj)

    @route('labels', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('admin')
    def edit_labels(self):
        form = ProposalLabelsAdminForm(model=Proposal, obj=self.obj, parent=self.obj.project)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Labels have been saved for this proposal."), 'info')
            return redirect(self.obj.url_for(), 303)
        else:
            flash(_("Labels could not be saved for this proposal."), 'error')
            return render_form(form, submit=_("Save changes"),
                title=_("Edit labels for '{}'").format(self.obj.title))


@route('/<project>/<url_id_name>', subdomain='<profile>')
class FunnelProposalView(ProposalView):
    pass


ProposalView.init_app(app)
FunnelProposalView.init_app(funnelapp)
