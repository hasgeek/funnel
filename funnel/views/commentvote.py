# -*- coding: utf-8 -*-

from flask import redirect, g, flash, request, render_template, get_template_attribute
from coaster.views import jsonp, load_models
from baseframe import _
from baseframe.forms import Form

from .. import app, lastuser
from ..models import *


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/voteup', methods=['POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_voteup(space, proposal):
    if request.is_xhr and Form().validate_on_submit():
        proposal.votes.vote(g.user, votedown=False)
        db.session.commit()
        return render_template('proposal_votes.html', proposal=proposal)
    else:
        return (_("Voting link timed out, please refresh the page."), 401)


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/votedown', methods=['POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_votedown(space, proposal):
    if request.is_xhr and Form().validate_on_submit():
        proposal.votes.vote(g.user, votedown=True)
        db.session.commit()
        return render_template('proposal_votes.html', proposal=proposal)
    else:
        return (_("Voting link timed out, please refresh the page."), 401)


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/cancelvote', methods=['POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_cancelvote(space, proposal):
    if request.is_xhr and Form().validate_on_submit():
        proposal.votes.cancelvote(g.user)
        db.session.commit()
        return render_template('proposal_votes.html', proposal=proposal)
    else:
        return (_("Voting link timed out, please refresh the page."), 401)


@app.route('/<space>/<proposal>/comments/<int:comment>/json')
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='view', addlperms=lastuser.permissions)
def comment_json(space, proposal, comment):
    if comment:
        return jsonp(message=comment.message.text)
    else:
        return jsonp(message='')


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/comments/<int:comment>/voteup')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_voteup(space, proposal, comment):
    comment.votes.vote(g.user, votedown=False)
    db.session.commit()
    if request.is_xhr:
        commentvote = get_template_attribute('comments.html', 'commentvote')
        return commentvote(proposal=proposal)
    else:
        flash(_("Your vote has been recorded"), 'info')
        return redirect(comment.url_for(proposal=proposal))


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/comments/<int:comment>/votedown')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_votedown(space, proposal, comment):
    comment.votes.vote(g.user, votedown=True)
    db.session.commit()
    if request.is_xhr:
        commentvote = get_template_attribute('comments.html', 'commentvote')
        return commentvote(proposal=proposal)
    else:
        flash(_("Your vote has been recorded"), 'info')
        return redirect(comment.url_for(proposal=proposal))


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/comments/<int:comment>/cancelvote')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_cancelvote(space, proposal, comment):
    comment.votes.cancelvote(g.user)
    db.session.commit()
    if request.is_xhr:
        commentvote = get_template_attribute('comments.html', 'commentvote')
        return commentvote(proposal=proposal)
    else:
        flash(_("Your vote has been withdrawn"), 'info')
        return redirect(comment.url_for(proposal=proposal))
