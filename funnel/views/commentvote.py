# -*- coding: utf-8 -*-

from flask import redirect, g, flash, abort, jsonify, request
from coaster.views import jsonp, load_models, route, requires_permission, UrlForView, ModelView
from baseframe import _, forms

from .. import app, funnelapp, lastuser
from ..models import db, Profile, Project, ProjectRedirect, Proposal, ProposalRedirect, Comment
from .mixins import ProposalViewMixin, CommentViewMixin


@route('/<profile>/<project>/<proposal>')
class ProposalVoteView(ProposalViewMixin, UrlForView, ModelView):
    @route('voteup', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote-proposal')
    def voteup(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(g.user, votedown=False)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('votedown', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote-proposal')
    def votedown(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(g.user, votedown=True)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('cancelvote', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote-proposal')
    def cancelvote(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.cancelvote(g.user)
        db.session.commit()
        message = _("Your vote has been withdrawn")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)


@route('/<project>/<proposal>', subdomain='<profile>')
class FunnelProposalVoteView(ProposalVoteView):
    pass


ProposalVoteView.init_app(app)
FunnelProposalVoteView.init_app(funnelapp)


@route('/<profile>/<project>/<proposal>/comments/<int:comment>')
class CommentView(CommentViewMixin, UrlForView, ModelView):
    @route('json')
    @requires_permission('view')
    def json(self):
        return jsonp(message=self.obj.message.text)

    @route('voteup', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote-comment')
    def voteup(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(g.user, votedown=False)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.proposal.url_for(), code=303)

    @route('votedown', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote-comment')
    def votedown(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(g.user, votedown=True)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.proposal.url_for(), code=303)

    @route('cancelvote', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote-comment')
    def cancelvote(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.cancelvote(g.user)
        db.session.commit()
        message = _("Your vote has been withdrawn")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.proposal.url_for(), code=303)



@route('/<project>/<proposal>/comments/<int:comment>', subdomain='<profile>')
class FunnelCommentView(CommentViewMixin, UrlForView, ModelView):
    pass


CommentView.init_app(app)
FunnelCommentView.init_app(funnelapp)
