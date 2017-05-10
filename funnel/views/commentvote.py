# -*- coding: utf-8 -*-

from flask import redirect, g, flash, abort, jsonify, request
from coaster.views import jsonp, load_models
from baseframe import _, forms

from .. import app, lastuser
from ..models import db, Profile, ProposalSpace, ProposalSpaceRedirect, Proposal, ProposalRedirect, Comment


@app.route('/<space>/<proposal>/voteup', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_voteup(profile, space, proposal):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    proposal.votes.vote(g.user, votedown=False)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(proposal.url_for(), code=303)


@app.route('/<space>/<proposal>/votedown', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_votedown(profile, space, proposal):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    proposal.votes.vote(g.user, votedown=True)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(proposal.url_for(), code=303)


@app.route('/<space>/<proposal>/cancelvote', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_cancelvote(profile, space, proposal):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    proposal.votes.cancelvote(g.user)
    db.session.commit()
    message = _("Your vote has been withdrawn")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(proposal.url_for(), code=303)


@app.route('/<space>/<proposal>/comments/<int:comment>/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='view', addlperms=lastuser.permissions)
def comment_json(profile, space, proposal, comment):
    if comment:
        return jsonp(message=comment.message.text)
    else:
        return jsonp(message='')


@app.route('/<space>/<proposal>/comments/<int:comment>/voteup', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_voteup(profile, space, proposal, comment):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    comment.votes.vote(g.user, votedown=False)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(comment.url_for(proposal=proposal), code=303)


@app.route('/<space>/<proposal>/comments/<int:comment>/votedown', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_votedown(profile, space, proposal, comment):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    comment.votes.vote(g.user, votedown=True)
    db.session.commit()
    message = _("Your vote has been recorded")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(comment.url_for(proposal=proposal), code=303)


@app.route('/<space>/<proposal>/comments/<int:comment>/cancelvote', subdomain='<profile>', methods=['POST'])
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_cancelvote(profile, space, proposal, comment):
    csrf_form = forms.Form()
    if not csrf_form.validate_on_submit():
        abort(403)
    comment.votes.cancelvote(g.user)
    db.session.commit()
    message = _("Your vote has been withdrawn")
    if request.is_xhr:
        return jsonify(message=message, code=200)
    flash(message, 'info')
    return redirect(comment.url_for(proposal=proposal), code=303)
