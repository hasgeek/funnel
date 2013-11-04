# -*- coding: utf-8 -*-

from flask import redirect, g, flash
from coaster.views import jsonp, load_models
from baseframe import _

from .. import app, lastuser
from ..models import *


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/voteup')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_voteup(space, proposal):
    proposal.votes.vote(g.user, votedown=False)
    db.session.commit()
    flash(_("Your vote has been recorded"), 'info')
    return redirect(proposal.url_for())


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/votedown')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_votedown(space, proposal):
    proposal.votes.vote(g.user, votedown=True)
    db.session.commit()
    flash(_("Your vote has been recorded"), 'info')
    return redirect(proposal.url_for())


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<space>/<proposal>/cancelvote')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='vote-proposal', addlperms=lastuser.permissions)
def proposal_cancelvote(space, proposal):
    proposal.votes.cancelvote(g.user)
    db.session.commit()
    flash(_("Your vote has been withdrawn"), 'info')
    return redirect(proposal.url_for())


@app.route('/<space>/<proposal>/comments/<int:comment>/json')
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    (Comment, {'id': 'comment'}, 'comment'),
    permission='view', addlperms=lastuser.permissions)
def comment_json(space, proposal, comment):
    if comment:
        return jsonp(message=comment.message)
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
    flash(_("Your vote has been withdrawn"), 'info')
    return redirect(comment.url_for(proposal=proposal))
