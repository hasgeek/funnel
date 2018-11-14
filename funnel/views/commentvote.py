# -*- coding: utf-8 -*-

from flask import redirect, g, flash, abort, jsonify, request
from coaster.views import jsonp, load_models
from baseframe import _, forms

from .. import app, funnelapp, lastuser
from ..models import db, Profile, Project, ProjectRedirect, Proposal, ProposalRedirect, Comment


@app.route('/<profile>/<project>/<proposal>/voteup', methods=['POST'])
@funnelapp.route('/<project>/<proposal>/voteup', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_voteup(profile, project, proposal):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    proposal.voteset.vote(g.user, votedown=False)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(proposal.url_for(), code=303)


@app.route('/<profile>/<project>/<proposal>/votedown', methods=['POST'])
@funnelapp.route('/<project>/<proposal>/votedown', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_votedown(profile, project, proposal):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    proposal.voteset.vote(g.user, votedown=True)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(proposal.url_for(), code=303)


@app.route('/<profile>/<project>/<proposal>/cancelvote', methods=['POST'])
@funnelapp.route('/<project>/<proposal>/cancelvote', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_cancelvote(profile, project, proposal):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    proposal.voteset.cancelvote(g.user)
    db.session.commit()
    message = _("Your vote has been withdrawn")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(proposal.url_for(), code=303)


@app.route('/<profile>/<project>/<proposal>/comments/<int:comment>/json')
@funnelapp.route('/<project>/<proposal>/comments/<int:comment>/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='view', addlperms=lastuser.permissions)
def comment_json(profile, project, proposal, comment):
    if comment:
        return jsonp(message=comment.message.text)
    else:
        return jsonp(message='')


@app.route('/<profile>/<project>/<proposal>/comments/<int:comment>/voteup', methods=['POST'])
@funnelapp.route('/<project>/<proposal>/comments/<int:comment>/voteup', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_voteup(profile, project, proposal, comment):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    comment.voteset.vote(g.user, votedown=False)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(comment.url_for(proposal=proposal), code=303)


@app.route('/<profile>/<project>/<proposal>/comments/<int:comment>/votedown', methods=['POST'])
@funnelapp.route('/<project>/<proposal>/comments/<int:comment>/votedown', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_votedown(profile, project, proposal, comment):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    comment.voteset.vote(g.user, votedown=True)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(comment.url_for(proposal=proposal), code=303)


@app.route('/<profile>/<project>/<proposal>/comments/<int:comment>/cancelvote', methods=['POST'])
@funnelapp.route('/<project>/<proposal>/comments/<int:comment>/cancelvote', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_cancelvote(profile, project, proposal, comment):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    comment.voteset.cancelvote(g.user)
    db.session.commit()
    message = _("Your vote has been withdrawn")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(comment.url_for(proposal=proposal), code=303)
