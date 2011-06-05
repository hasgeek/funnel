# -*- coding: utf-8 -*-

import urlparse
from markdown import Markdown

from flask import render_template, redirect, request, g, url_for, Markup, abort, flash
from flaskext.lastuser import LastUser
from flaskext.lastuser.sqlalchemy import UserManager

from app import app
from models import *
from forms import ProposalSpaceForm, SectionForm, ProposalForm, CommentForm
from utils import makename

lastuser = LastUser(app)
lastuser.init_usermanager(UserManager(db, User))

markdown = Markdown(safe_mode="escape").convert

# --- Utilities ---------------------------------------------------------------

def get_next_url(referrer=False, external=False):
    """
    Get the next URL to redirect to. Don't return external URLs unless
    explicitly asked for. This is to protect the site from being an unwitting
    redirector to external URLs.
    """
    next_url = request.args.get('next', '')
    if not external:
        if next_url.startswith('http:') or next_url.startswith('https:') or next_url.startswith('//'):
            # Do the domains match?
            if urlparse.urlsplit(next_url).hostname != urlparse.urlsplit(request.url).hostname:
                next_url = ''
    if referrer:
        return next_url or request.referrer or url_for('index')
    else:
        return next_url or url_for('index')


# --- Routes ------------------------------------------------------------------

@app.route('/')
def index():
    spaces = ProposalSpace.query.filter(ProposalSpace.status >= 1 and ProposalSpace.status <= 4).all()
    return render_template('index.html', spaces=spaces)


@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='img/favicon.ico')


@app.route('/login')
@lastuser.login_handler
def login():
    return {'scope': 'id'}


@app.route('/logout')
@lastuser.logout_handler
def logout():
    flash("You are now logged out", category='info')
    return get_next_url()


@app.route('/login/redirect')
@lastuser.auth_handler
def lastuserauth():
    # Save the user object
    db.session.commit()
    return redirect(get_next_url())


@lastuser.auth_error_handler
def lastuser_error(error, error_description=None, error_uri=None):
    if error == 'access_denied':
        flash("You denied the request to login", category='error')
        return redirect(get_next_url())
    return render_template("autherror.html",
        error=error,
        error_description=error_description,
        error_uri=error_uri)

# --- Routes: account ---------------------------------------------------------

@app.route('/account')
def account():
    return "Coming soon"


# --- Routes: spaces ----------------------------------------------------------

@app.route('/new', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
def newspace():
    form = ProposalSpaceForm()
    if form.validate_on_submit():
        space = ProposalSpace(user=g.user)
        form.populate_obj(space)
        space.description_html = markdown(space.description)
        db.session.add(space)
        db.session.commit()
        flash("Your new space has been created", "info")
        return redirect(url_for('viewspace', name=space.name), code=303)
    return render_template('autoform.html', form=form, title="Create a new proposal space", submit="Create space")


@app.route('/<name>/')
def viewspace(name):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    description = Markup(space.description_html)
    tracks = ProposalSpaceSection.query.filter_by(proposal_space=space).order_by('title').all()
    proposals = Proposal.query.filter_by(proposal_space=space).order_by('created_at').all()
    return render_template('space.html', space=space, description=description, tracks=tracks, proposals=proposals)


@app.route('/<name>/edit', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
def editspace(name):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    form = ProposalSpaceForm()
    if request.method == 'GET':
        form.name.data = space.name
        form.title.data = space.title
        form.datelocation.data = space.datelocation
        form.tagline.data = space.tagline
        form.description.data = space.description
        form.status.data = space.status
    if form.validate_on_submit():
        form.populate_obj(space)
        space.description_html = markdown(space.description)
        db.session.commit()
        flash("Your changes have been saved", "info")
        return redirect(url_for('viewspace', name=space.name), code=303)
    return render_template('autoform.html', form=form, title="Edit proposal space", submit="Save changes")


@app.route('/<name>/newsection', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
def newsection(name):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    form = SectionForm()
    if form.validate_on_submit():
        section = ProposalSpaceSection(proposal_space=space)
        form.populate_obj(section)
        db.session.add(section)
        db.session.commit()
        flash("Your new section has been added", "info")
        return redirect(url_for('viewspace', name=space.name), code=303)
    return render_template('autoform.html', form=form, title="New section", submit="Create section")


@app.route('/<name>/new', methods=['GET', 'POST'])
@lastuser.requires_login
def newsession(name):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    if space.status != SPACESTATUS.SUBMISSIONS:
        abort(403)
    form = ProposalForm()
    form.section.query = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title')
    if form.validate_on_submit():
        proposal = Proposal(user=g.user, proposal_space=space)
        proposal.votes.vote(g.user) # Vote up your own proposal by default
        form.populate_obj(proposal)
        proposal.name = makename(proposal.title)
        proposal.objective_html = markdown(proposal.objective)
        proposal.description_html = markdown(proposal.description)
        proposal.requirements_html = markdown(proposal.requirements)
        db.session.add(proposal)
        db.session.commit()
        flash("Your new session has been saved", "info")
        return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    return render_template('autoform.html', form=form, title="Submit a session proposal", submit="Submit session",
        breadcrumbs = [(url_for('viewspace', name=space.name), space.title)])


@app.route('/<name>/<slug>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
def editsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    proposal_id = slug.split('-')[0]
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    if proposal.user != g.user:
        abort(403)
    form = ProposalForm()
    form.section.query = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title')
    if request.method == 'GET':
        form.title.data = proposal.title
        form.section.data = proposal.section
        form.objective.data = proposal.objective
        form.session_type.data = proposal.session_type
        form.technical_level.data = proposal.technical_level
        form.description.data = proposal.description
        form.requirements.data = proposal.requirements
        form.slides.data = proposal.slides
        form.links.data = proposal.links
    if form.validate_on_submit():
        form.populate_obj(proposal)
        proposal.name = makename(proposal.title)
        proposal.objective_html = markdown(proposal.objective)
        proposal.description_html = markdown(proposal.description)
        proposal.requirements_html = markdown(proposal.requirements)
        db.session.commit()
        flash("Your changes have been saved", "info")
        return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    return render_template('autoform.html', form=form, title="Edit session proposal", submit="Save changes",
        breadcrumbs = [(url_for('viewspace', name=space.name), space.title),
                       (url_for('viewsession', name=space.name, slug=proposal.urlname), proposal.title)])


@app.route('/<name>/<slug>', methods=['GET', 'POST'])
def viewsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    try:
        proposal_id = int(slug.split('-')[0])
    except ValueError:
        abort(404)
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    if proposal.proposal_space != space:
        return redirect(url_for('viewsession', name=proposal.proposal_space.name, slug=proposal.urlname), code=301)
    if slug != proposal.urlname:
        return redirect(url_for('viewsession', name=proposal.proposal_space.name, slug=proposal.urlname), code=301)
    # URL is okay. Show the proposal.
    comments = Comment.query.filter_by(commentspace=proposal.comments).order_by('created_at').all()
    commentform = CommentForm()
    if request.method == 'POST':
        if request.form.get('form.id') == 'newcomment' and commentform.validate():
            newcomment = Comment(user=g.user, commentspace=proposal.comments, message=commentform.message.data)
            newcomment.message_html = markdown(newcomment.message)
            db.session.add(newcomment)
            db.session.commit()
            flash("Your comment has been saved", "info")
            # Redirect despite this being the same page because HTTP 303 is required to not break
            # the browser Back button
            return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname)+"#comment-"+str(newcomment.id), code=303)
    return render_template('proposal.html', space=space, proposal=proposal,
        comments = comments, commentform = commentform,
        breadcrumbs = [(url_for('viewspace', name=space.name), space.title)])


@app.route('/<name>/<slug>/voteup')
@lastuser.requires_login
def voteupsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    try:
        proposal_id = int(slug.split('-')[0])
    except ValueError:
        abort(404)
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    proposal.votes.vote(g.user, votedown=False)
    db.session.commit()
    flash("Your vote has been recorded", "info")
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname))


@app.route('/<name>/<slug>/votedown')
@lastuser.requires_login
def votedownsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    try:
        proposal_id = int(slug.split('-')[0])
    except ValueError:
        abort(404)
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    proposal.votes.vote(g.user, votedown=True)
    db.session.commit()
    flash("Your vote has been recorded", "info")
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname))


@app.route('/<name>/<slug>/cancelvote')
@lastuser.requires_login
def votecancelsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    try:
        proposal_id = int(slug.split('-')[0])
    except ValueError:
        abort(404)
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    proposal.votes.cancelvote(g.user)
    db.session.commit()
    flash("Your vote has been withdrawn", "info")
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname))


@app.route('/<name>/<slug>/next')
def nextsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    try:
        proposal_id = int(slug.split('-')[0])
    except ValueError:
        abort(404)
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)

    next = proposal.getnext()
    if next:
        return redirect(url_for('viewsession', name=space.name, slug=next.urlname))
    else:
        flash("You were at the last proposal", "info")
        return redirect(url_for('viewspace', name=space.name))


@app.route('/<name>/<slug>/prev')
def prevsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    try:
        proposal_id = int(slug.split('-')[0])
    except ValueError:
        abort(404)
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)

    prev = proposal.getprev()
    if prev:
        return redirect(url_for('viewsession', name=space.name, slug=prev.urlname))
    else:
        flash("You were at the first proposal", "info")
        return redirect(url_for('viewspace', name=space.name))
