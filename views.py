# -*- coding: utf-8 -*-

import urlparse
from datetime import datetime, timedelta
from markdown import Markdown

from flask import render_template, redirect, request, g, url_for, Markup, abort, flash, jsonify
from flaskext.lastuser import LastUser
from flaskext.lastuser.sqlalchemy import UserManager

from app import app
from models import *
from forms import ProposalSpaceForm, SectionForm, ProposalForm, CommentForm, DeleteCommentForm
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
    return {'scope': 'id email'}


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
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).order_by('title').all()
    proposals = Proposal.query.filter_by(proposal_space=space).order_by(db.desc('created_at')).all()
    return render_template('space.html', space=space, description=description, sections=sections, proposals=proposals)

@app.route('/<name>/json')
def viewspace_json(name):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    description = Markup(space.description_html)
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).order_by('title').all()
    proposals = Proposal.query.filter_by(proposal_space=space).order_by(db.desc('created_at')).all()
    return jsonify({
        'space': {
            'name': space.name,
            'title': space.title,
            'datelocation': space.datelocation,
            'status': space.status,
            },
        'sections': [ {'name': s.name, 'title': s.title, 'description': s.description} for s in sections ],
        'proposals': [ {
            'id': proposal.id,
            'name': proposal.urlname,
            'title': proposal.title,
            'url': url_for('viewsession', name=space.name, slug=proposal.urlname, _external=True),
            'proposer': proposal.user.fullname,
            'speaker': proposal.speaker.fullname if proposal.speaker else '(open)',
            'section': proposal.section.title,
            'type': proposal.session_type,
            'level': proposal.technical_level,
            'votes': proposal.votes.count,
            'comments': proposal.comments.count,
            'submitted': proposal.created_at.isoformat(),
            } for proposal in proposals ]
        })


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
    form.email.data = g.user.email
    if form.validate_on_submit():
        proposal = Proposal(user=g.user, proposal_space=space)
        if form.speaking.data:
            proposal.speaker = g.user
        else:
            proposal.speaker = None
        proposal.votes.vote(g.user) # Vote up your own proposal by default
        form.populate_obj(proposal)
        proposal.name = makename(proposal.title)
        proposal.objective_html = markdown(proposal.objective)
        proposal.description_html = markdown(proposal.description)
        proposal.requirements_html = markdown(proposal.requirements)
        proposal.bio_html = markdown(proposal.bio)
        db.session.add(proposal)
        db.session.commit()
        flash("Your new session has been saved", "info")
        return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    return render_template('autoform.html', form=form, title="Submit a session proposal", submit="Submit session",
        breadcrumbs = [(url_for('viewspace', name=space.name), space.title)], message=
        Markup('This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.'))


@app.route('/<name>/<slug>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
def editsession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    proposal_id = int(slug.split('-')[0])
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    if proposal.user != g.user:
        abort(403)
    form = ProposalForm()
    form.section.query = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title')
    if request.method == 'GET':
        form.email.data = proposal.email
        form.title.data = proposal.title
        form.section.data = proposal.section
        form.objective.data = proposal.objective
        form.session_type.data = proposal.session_type
        form.technical_level.data = proposal.technical_level
        form.description.data = proposal.description
        form.requirements.data = proposal.requirements
        form.slides.data = proposal.slides
        form.links.data = proposal.links
        form.bio.data = proposal.bio
        form.speaking.data = proposal.speaker == g.user
    if form.validate_on_submit():
        form.populate_obj(proposal)
        proposal.name = makename(proposal.title)
        if form.speaking.data:
            proposal.speaker = g.user
        else:
            if proposal.speaker == g.user:
                proposal.speaker = None
        proposal.objective_html = markdown(proposal.objective)
        proposal.description_html = markdown(proposal.description)
        proposal.requirements_html = markdown(proposal.requirements)
        proposal.bio_html = markdown(proposal.bio)
        proposal.edited_at = datetime.utcnow()
        db.session.commit()
        flash("Your changes have been saved", "info")
        return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    return render_template('autoform.html', form=form, title="Edit session proposal", submit="Save changes",
        breadcrumbs = [(url_for('viewspace', name=space.name), space.title),
                       (url_for('viewsession', name=space.name, slug=proposal.urlname), proposal.title)],
        message = Markup('This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.'))


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
    comments = sorted(Comment.query.filter_by(commentspace=proposal.comments, parent=None).order_by('created_at').all(),
        key=lambda c:c.votes.count, reverse=True)
    commentform = CommentForm()
    delcommentform = DeleteCommentForm()
    if request.method == 'POST':
        if request.form.get('form.id') == 'newcomment' and commentform.validate():
            if commentform.edit_id.data:
                comment = Comment.query.get(int(commentform.edit_id.data))
                if comment:
                    if comment.user == g.user:
                        comment.message = commentform.message.data
                        comment.message_html = markdown(comment.message)
                        comment.edited_at = datetime.utcnow()
                        flash("Your comment has been edited", "info")
                    else:
                        flash("You can only edit your own comments", "info")
                else:
                    flash("No such comment", "error")
            else:
                comment = Comment(user=g.user, commentspace=proposal.comments, message=commentform.message.data)
                if commentform.parent_id.data:
                    parent = Comment.query.get(int(commentform.parent_id.data))
                    if parent and parent.commentspace == proposal.comments:
                        comment.parent = parent
                comment.message_html = markdown(comment.message)
                proposal.comments.count += 1
                comment.votes.vote(g.user) # Vote for your own comment
                db.session.add(comment)
                flash("Your comment has been posted", "info")
            db.session.commit()
            # Redirect despite this being the same page because HTTP 303 is required to not break
            # the browser Back button
            return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname)+"#c"+str(comment.id), code=303)
        elif request.form.get('form.id') == 'delcomment' and delcommentform.validate():
            comment = Comment.query.get(int(delcommentform.comment_id.data))
            if comment:
                if comment.user == g.user:
                    comment.delete()
                    proposal.comments.count -= 1
                    db.session.commit();
                    flash("Your comment was deleted.", "info")
                else:
                    flash("You did not post that comment.", "error")
            else:
                flash("No such comment.", "error")
            return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    return render_template('proposal.html', space=space, proposal=proposal,
        comments = comments, commentform = commentform, delcommentform = delcommentform,
        breadcrumbs = [(url_for('viewspace', name=space.name), space.title)])


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
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


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
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


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
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


@app.route('/<name>/<slug>/comments/<int:cid>/json')
def jsoncomment(name, slug, cid):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    proposal_id = int(slug.split('-')[0])
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)

    comment = Comment.query.get(cid)
    if comment:
        return jsonify(message=comment.message)
    else:
        return jsonify(message='')


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<name>/<slug>/comments/<int:cid>/voteup')
@lastuser.requires_login
def voteupcomment(name, slug, cid):
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
    comment = Comment.query.get(cid)
    if not comment:
        abort(404)
    comment.votes.vote(g.user, votedown=False)
    db.session.commit()
    flash("Your vote has been recorded", "info")
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname)+"#c%d" % cid)


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<name>/<slug>/comments/<int:cid>/votedown')
@lastuser.requires_login
def votedowncomment(name, slug, cid):
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
    comment = Comment.query.get(cid)
    if not comment:
        abort(404)
    comment.votes.vote(g.user, votedown=True)
    db.session.commit()
    flash("Your vote has been recorded", "info")
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname)+"#c%d" % cid)


# FIXME: This voting method uses GET but makes db changes. Not correct. Should be POST
@app.route('/<name>/<slug>/comments/<int:cid>/cancelvote')
@lastuser.requires_login
def votecancelcomment(name, slug, cid):
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
    comment = Comment.query.get(cid)
    if not comment:
        abort(404)
    comment.votes.cancelvote(g.user)
    db.session.commit()
    flash("Your vote has been withdrawn", "info")
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname)+"#c%d" % cid)


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


@app.template_filter('age')
def age(dt):
    suffix = u"ago"
    delta = datetime.utcnow() - dt
    if delta.days == 0:
        # < 1 day
        if delta.seconds < 10:
            return "seconds %s" % suffix
        elif delta.seconds < 60:
            return "%d seconds %s" % (delta.seconds, suffix)
        elif delta.seconds < 120:
            return "a minute %s" % suffix
        elif delta.seconds < 3600: # < 1 hour
            return "%d minutes %s" % (int(delta.seconds / 60), suffix)
        elif delta.seconds < 7200: # < 2 hours
            return "an hour %s" % suffix
        else:
            return "%d hours %s" % (int(delta.seconds / 3600), suffix)
    elif delta.days == 1:
        return u"a day %s" % suffix
    else:
        return u"%d days %s" % (delta.days, suffix)
