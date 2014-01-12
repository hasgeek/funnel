# -*- coding: utf-8 -*-

from flask import redirect, g, flash, request, render_template, get_template_attribute
from coaster.views import jsonp, load_models
from baseframe import _
from baseframe.forms import Form

from .. import app, lastuser
from ..models import *


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


@app.route('/<space>/<proposal>/comments/<int:comment>/voteup', methods=['POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_voteup(space, proposal, comment):
    if request.is_xhr and Form().validate_on_submit():
        comment.votes.vote(g.user, votedown=False)
        db.session.commit()
        return render_template('proposal_comment_votes.html', comment=comment, currentuser=g.user, votelinkbase=proposal.url_for() + '/comments')
    else:
        return (_("Voting link timed out, please refresh the page."), 401)


@app.route('/<space>/<proposal>/comments/<int:comment>/votedown', methods=['POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_votedown(space, proposal, comment):
    if request.is_xhr and Form().validate_on_submit():
        comment.votes.vote(g.user, votedown=True)
        db.session.commit()
        return render_template('proposal_comment_votes.html', comment=comment, currentuser=g.user, votelinkbase=proposal.url_for() + '/comments')
    else:
        return (_("Voting link timed out, please refresh the page."), 401)


@app.route('/<space>/<proposal>/comments/<int:comment>/cancelvote', methods=['POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='vote-comment', addlperms=lastuser.permissions)
def comment_cancelvote(space, proposal, comment):
    if request.is_xhr and Form().validate_on_submit():
        comment.votes.cancelvote(g.user)
        db.session.commit()
        return render_template('proposal_comment_votes.html', comment=comment, currentuser=g.user, votelinkbase=proposal.url_for() + '/comments')
    else:
        return (_("Voting link timed out, please refresh the page."), 401)
