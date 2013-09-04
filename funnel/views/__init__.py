# -*- coding: utf-8 -*-

import re
from datetime import datetime
import unicodecsv
from cStringIO import StringIO
from pytz import timezone, utc
from pytz.exceptions import UnknownTimeZoneError

from flask import (
    render_template,
    redirect,
    request,
    g,
    url_for,
    Markup,
    abort,
    flash,
    escape,
    Response)
from flask.ext.mail import Message
from coaster.views import get_next_url, jsonp, load_models, load_model
from coaster.gfm import markdown

from .. import app, mail, lastuser
from ..models import *
from ..forms import (
    ProposalSpaceForm,
    SectionForm,
    UserGroupForm,
    ProposalForm,
    CommentForm,
    DeleteCommentForm,
    ConfirmDeleteForm,
    ConfirmSessionForm)
from coaster import make_name

jsoncallback_re = re.compile(r'^[a-z$_][0-9a-z$_]*$', re.I)

# From http://daringfireball.net/2010/07/improved_regex_for_matching_urls
url_re = re.compile(ur'''(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''')

proposal_headers = [
    'id',
    'title',
    'url',
    'proposer',
    'speaker',
    'email',
    'phone',
    'section',
    'type',
    'level',
    'votes',
    'comments',
    'submitted',
    'confirmed'
    ]

# --- Routes ------------------------------------------------------------------


@app.route('/')
def index():
    spaces = ProposalSpace.query.filter(ProposalSpace.status >= 1).filter(ProposalSpace.status <= 4).order_by(ProposalSpace.date.desc()).all()
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


@app.route('/login/notify', methods=['POST'])
@lastuser.notification_handler
def lastusernotify(user):
    # Save the user object
    db.session.commit()


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
    form.description.flags.markdown = True
    if form.validate_on_submit():
        space = ProposalSpace(user=g.user)
        form.populate_obj(space)
        space.description_html = markdown(space.description)
        db.session.add(space)
        db.session.commit()
        flash("Your new space has been created", "info")
        return redirect(url_for('viewspace', name=space.name), code=303)
    return render_template('baseframe/autoform.html', form=form, title="Create a new proposal space", submit="Create space")


@app.route('/<name>/')
def viewspace(name):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    description = Markup(space.description_html)
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).order_by('title').all()
    confirmed = Proposal.query.filter_by(proposal_space=space, confirmed=True).order_by(db.desc('created_at')).all()
    unconfirmed = Proposal.query.filter_by(proposal_space=space, confirmed=False).order_by(db.desc('created_at')).all()
    return render_template('space.html', space=space, description=description, sections=sections,
        confirmed=confirmed, unconfirmed=unconfirmed, is_siteadmin=lastuser.has_permission('siteadmin'))


@app.route('/<name>/json')
def viewspace_json(name):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).order_by('title').all()
    proposals = Proposal.query.filter_by(proposal_space=space).order_by(db.desc('created_at')).all()
    return jsonp(**{
        'space': {
            'name': space.name,
            'title': space.title,
            'datelocation': space.datelocation,
            'status': space.status,
            },
        'sections': [{'name': s.name, 'title': s.title, 'description': s.description} for s in sections],
        'proposals': [proposal_data(proposal) for proposal in proposals]
        })


@app.route('/<name>/csv')
def viewspace_csv(name):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    if lastuser.has_permission('siteadmin'):
        usergroups = [g.name for g in space.usergroups]
    else:
        usergroups = []
    proposals = Proposal.query.filter_by(proposal_space=space).order_by(db.desc('created_at')).all()
    outfile = StringIO()
    out = unicodecsv.writer(outfile, encoding='utf-8')
    out.writerow(proposal_headers + ['votes_' + group for group in usergroups])
    for proposal in proposals:
        out.writerow(proposal_data_flat(proposal, usergroups))
    outfile.seek(0)
    return Response(unicode(outfile.getvalue(), 'utf-8'), mimetype='text/plain')


@app.route('/<name>/edit', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
def editspace(name):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    form = ProposalSpaceForm(obj=space)
    form.description.flags.markdown = True
    if form.validate_on_submit():
        form.populate_obj(space)
        space.description_html = markdown(space.description)
        db.session.commit()
        flash("Your changes have been saved", "info")
        return redirect(url_for('viewspace', name=space.name), code=303)
    return render_template('baseframe/autoform.html', form=form, title="Edit proposal space", submit="Save changes")


@app.route('/<name>/sections/new', methods=['GET', 'POST'])
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
    return render_template('baseframe/autoform.html', form=form, title="New section", submit="Create section")


@app.route('/<space>/sections/<section>/edit', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'))
def section_edit(space, section):
    form = SectionForm(obj=section)
    if form.validate_on_submit():
        form.populate_obj(section)
        db.session.commit()
        flash("Your section has been edited", "info")
        return redirect(url_for('viewspace', name=space.name), code=303)
    return render_template('baseframe/autoform.html', form=form, title="Edit section", submit="Edit section")


@app.route('/<space>/sections/<section>/delete', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'))
def section_delete(space, section):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        if 'delete' in request.form:
            db.session.delete(section)
            db.session.commit()
            flash("Your section has been deleted", "info")
        return redirect(url_for('viewspace', name=space.name), code=303)
    return render_template('delete.html', form=form, title=u"Confirm delete",
        message=u"Do you really wish to delete section '%s'?" % section.title)


@app.route('/<space>/sections')
@lastuser.requires_permission('siteadmin')
@load_model(ProposalSpace, {'name': 'space'}, 'space')
def sections_list(space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).all()
    return render_template('sections.html', space=space, sections=sections)


@app.route('/<space>/sections/<section>')
@lastuser.requires_permission('siteadmin')
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'))
def section_view(space, section):
    return render_template('section.html', space=space, section=section)


@app.route('/<name>/users')
@lastuser.requires_permission('siteadmin')
def usergroup_list(name):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    return render_template('usergroups.html', space=space, usergroups=space.usergroups)


@app.route('/<name>/users/<group>')
@lastuser.requires_permission('siteadmin')
def usergroup_view(name, group):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    usergroup = UserGroup.query.filter_by(name=group, proposal_space=space).first_or_404()
    return render_template('usergroup.html', space=space, usergroup=usergroup)


@app.route('/<name>/users/new', defaults={'group': None}, endpoint='usergroup_new', methods=['GET', 'POST'])
@app.route('/<name>/users/<group>/edit', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
def usergroup_edit(name, group):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    form = UserGroupForm()
    if group is not None:
        usergroup = UserGroup.query.filter_by(name=group, proposal_space=space).first_or_404()
        if request.method == 'GET':
            form.name.data = usergroup.name
            form.title.data = usergroup.title
            form.users.data = '\r\n'.join([u.email or u.username or '' for u in usergroup.users])
    if form.validate_on_submit():
        if group is None:
            usergroup = UserGroup(proposal_space=space)
        usergroup.name = form.name.data
        usergroup.title = form.title.data
        formdata = [line.strip() for line in
            form.users.data.replace('\r', '\n').replace(',', '\n').split('\n') if line]
        usersdata = lastuser.getusers(names=formdata)
        users = []
        for userdata in usersdata:
            user = User.query.filter_by(userid=userdata['userid']).first()
            if user is None:
                user = User(userid=userdata['userid'], username=userdata['name'], fullname=userdata['title'])
                db.session.add(user)
            users.append(user)
        usergroup.users = users
        db.session.commit()
        return redirect(url_for('usergroup_view', name=space.name, group=usergroup.name), code=303)
    if group is None:
        return render_template('baseframe/autoform.html', form=form, title="New user group", submit="Create")
    else:
        return render_template('baseframe/autoform.html', form=form, title="Edit user group", submit="Save")


@app.route('/<name>/users/<group>/delete', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
def usergroup_delete(name, group):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    usergroup = UserGroup.query.filter_by(name=group, proposal_space=space).first_or_404()
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        if 'delete' in request.form:
            db.session.delete(usergroup)
            db.session.commit()
            flash("Your user group has been deleted", "info")
            return redirect(url_for('usergroup_list', name=name))
        else:
            return redirect(url_for('usergroup_view', name=name, group=group))
    return render_template('delete.html', form=form, title=u"Confirm delete",
        message=u"Do you really wish to delete user group '%s'?" % usergroup.title)


@app.route('/<name>/new', methods=['GET', 'POST'])
@lastuser.requires_login
def newsession(name):
    space = ProposalSpace.query.filter_by(name=name).first_or_404()
    if space.status != SPACESTATUS.SUBMISSIONS:
        abort(403)
    form = ProposalForm()
    del form.session_type  # We don't use this anymore
    form.section.query = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title')
    if len(list(form.section.query.all())) == 0:
        # Don't bother with sections when there aren't any
        del form.section
    if request.method == 'GET':
        form.email.data = g.user.email
    if form.validate_on_submit():
        proposal = Proposal(user=g.user, proposal_space=space)
        if form.speaking.data:
            proposal.speaker = g.user
        else:
            proposal.speaker = None
        proposal.votes.vote(g.user)  # Vote up your own proposal by default
        form.populate_obj(proposal)
        proposal.name = make_name(proposal.title)
        db.session.add(proposal)
        db.session.commit()
        flash("Your new session has been saved", "info")
        return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    return render_template('baseframe/autoform.html', form=form, title="Submit a session proposal", submit="Submit session",
        breadcrumbs=[(url_for('viewspace', name=space.name), space.title)],
        message=Markup(
            'This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.'))


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
    if proposal.user != g.user and not lastuser.has_permission('siteadmin'):
        abort(403)
    form = ProposalForm(obj=proposal)
    if not proposal.session_type:
        del form.session_type  # Remove this if we're editing a proposal that had no session type
    form.section.query = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title')
    if len(list(form.section.query.all())) == 0:
        # Don't bother with sections when there aren't any
        del form.section
    if proposal.user != g.user:
        del form.speaking
    elif request.method == 'GET':
        form.speaking.data = proposal.speaker == g.user
    if form.validate_on_submit():
        form.populate_obj(proposal)
        proposal.name = make_name(proposal.title)
        if proposal.user == g.user:
            # Only allow the speaker to change this status
            if form.speaking.data:
                proposal.speaker = g.user
            else:
                if proposal.speaker == g.user:
                    proposal.speaker = None
        proposal.edited_at = datetime.utcnow()
        db.session.commit()
        flash("Your changes have been saved", "info")
        return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    return render_template('baseframe/autoform.html', form=form, title="Edit session proposal", submit="Save changes",
        breadcrumbs=[(url_for('viewspace', name=space.name), space.title),
                     (url_for('viewsession', name=space.name, slug=proposal.urlname), proposal.title)],
        message=Markup(
            'This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.'))


@app.route('/<name>/<slug>/confirm', methods=['POST'])
@lastuser.requires_permission('siteadmin')
def confirmsession(name, slug):
    ProposalSpace.query.filter_by(name=name).first_or_404()
    proposal_id = int(slug.split('-')[0])
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    form = ConfirmSessionForm()
    if form.validate_on_submit():
        proposal.confirmed = not proposal.confirmed
        db.session.commit()
        if proposal.confirmed:
            flash("This proposal has been confirmed.", 'success')
        else:
            flash("This session has been cancelled.", 'success')
    return redirect(url_for('viewsession', name=name, slug=slug))


@app.route('/<name>/<slug>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
def deletesession(name, slug):
    space = ProposalSpace.query.filter_by(name=name).first()
    if not space:
        abort(404)
    proposal_id = int(slug.split('-')[0])
    proposal = Proposal.query.get(proposal_id)
    if not proposal:
        abort(404)
    if not lastuser.has_permission('siteadmin') and proposal.user != g.user:
        abort(403)
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        if 'delete' in request.form:
            comments = Comment.query.filter_by(commentspace=proposal.comments).order_by('created_at').all()
            for comment in comments:
                db.session.delete(comment)
            db.session.delete(proposal.comments)
            votes = Vote.query.filter_by(votespace=proposal.votes).all()
            for vote in votes:
                db.session.delete(vote)
            db.session.delete(proposal.votes)
            db.session.delete(proposal)
            db.session.commit()
            flash("Your proposal has been deleted", "info")
            return redirect(url_for('viewspace', name=name))
        else:
            return redirect(url_for('viewsession', name=name, slug=slug))
    return render_template('delete.html', form=form, title=u"Confirm delete",
        message=u"Do you really wish to delete your proposal '%s'? "
                u"This will remove all votes and comments as well. This operation "
                u"is permanent and cannot be undone." % proposal.title)


def urllink(m):
    s = m.group(0)
    if not (s.startswith('http://') or s.startswith('https://')):
        s = 'http://' + s
    return '<a href="%s" rel="nofollow" target="_blank">%s</a>' % (s, s)


def send_mail(sender, to, body, subject):
    msg = Message(sender=sender, subject=subject, recipients=[to])
    msg.body = body
    msg.html = markdown(msg.body)
    mail.send(msg)


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
        key=lambda c: c.votes.count, reverse=True)
    commentform = CommentForm()
    commentform.message.flags.markdown = True
    delcommentform = DeleteCommentForm()
    if request.method == 'POST':
        if request.form.get('form.id') == 'newcomment' and commentform.validate():
            send_mail_info = []
            if commentform.comment_edit_id.data:
                comment = Comment.query.get(int(commentform.comment_edit_id.data))
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
                comment = Comment(user=g.user, commentspace=proposal.comments,
                    message=commentform.message.data)
                if commentform.parent_id.data:
                    parent = Comment.query.get(int(commentform.parent_id.data))
                    if parent.user.email:
                        if parent.user == proposal.user:  # check if parent comment & proposal owner are same
                            if not g.user == parent.user:  # check if parent comment is by proposal owner
                                send_mail_info.append({'to': proposal.user.email or proposal.email,
                                    'subject': "%s Funnel:%s" % (name, proposal.title),
                                    'template': 'proposal_comment_reply_email.md'})
                        else:  # send mail to parent comment owner & proposal owner
                            if not parent.user == g.user:
                                send_mail_info.append({'to': parent.user.email,
                                    'subject': "%s Funnel:%s" % (name, proposal.title),
                                    'template': 'proposal_comment_to_proposer_email.md'})
                            if not proposal.user == g.user:
                                send_mail_info.append({'to': proposal.user.email or proposal.email,
                                    'subject': "%s Funnel:%s" % (name, proposal.title),
                                    'template': 'proposal_comment_email.md'})

                    if parent and parent.commentspace == proposal.comments:
                        comment.parent = parent
                else:  # for top level comment
                    if not proposal.user == g.user:
                        send_mail_info.append({'to': proposal.user.email or proposal.email,
                            'subject': "%s Funnel:%s" % (name, proposal.title),
                            'template': 'proposal_comment_email.md'})
                comment.message_html = markdown(comment.message)
                proposal.comments.count += 1
                comment.votes.vote(g.user)  # Vote for your own comment
                db.session.add(comment)
                flash("Your comment has been posted", "info")
            db.session.commit()
            to_redirect = url_for('viewsession', name=space.name,
                    slug=proposal.urlname, _external=True) + "#c" + str(comment.id)
            for item in send_mail_info:
                email_body = render_template(item.pop('template'), proposal=proposal, comment=comment, link=to_redirect)
                send_mail(sender=None, body=email_body, **item)
            # Redirect despite this being the same page because HTTP 303 is required to not break
            # the browser Back button
            return redirect(to_redirect, code=303)
        elif request.form.get('form.id') == 'delcomment' and delcommentform.validate():
            comment = Comment.query.get(int(delcommentform.comment_id.data))
            if comment:
                if comment.user == g.user:
                    comment.delete()
                    proposal.comments.count -= 1
                    db.session.commit()
                    flash("Your comment was deleted.", "info")
                else:
                    flash("You did not post that comment.", "error")
            else:
                flash("No such comment.", "error")
            return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname), code=303)
    links = [Markup(url_re.sub(urllink, unicode(escape(l)))) for l in proposal.links.replace('\r\n', '\n').split('\n') if l]
    confirmform = ConfirmSessionForm()
    return render_template('proposal.html', space=space, proposal=proposal,
        comments=comments, commentform=commentform, delcommentform=delcommentform,
        breadcrumbs=[(url_for('viewspace', name=space.name), space.title)],
        links=links, confirmform=confirmform)


def proposal_data(proposal):
    """
    Return proposal data suitable for a JSON dump. Request helper, not to be used standalone.
    """
    votes_count = None
    votes_groups = None
    votes_bydate = dict([(g.name, {}) for g in proposal.proposal_space.usergroups])

    if 'tz' in request.args:
        try:
            tz = timezone(request.args['tz'])
        except UnknownTimeZoneError:
            abort(400)
    else:
        tz = None

    if lastuser.has_permission('siteadmin'):
        votes_count = len(proposal.votes.votes)
        votes_groups = dict([(g.name, 0) for g in proposal.proposal_space.usergroups])
        groupuserids = dict([(g.name, [u.userid for u in g.users]) for g in proposal.proposal_space.usergroups])
        for vote in proposal.votes.votes:
            for groupname, userids in groupuserids.items():
                if vote.user.userid in userids:
                    votes_groups[groupname] += -1 if vote.votedown else +1
                    if tz:
                        date = tz.normalize(vote.updated_at.replace(tzinfo=utc).astimezone(tz)).strftime('%Y-%m-%d')
                    else:
                        date = vote.updated_at.strftime('%Y-%m-%d')
                    votes_bydate[groupname].setdefault(date, 0)
                    votes_bydate[groupname][date] += -1 if vote.votedown else +1

    return {'id': proposal.id,
            'name': proposal.urlname,
            'title': proposal.title,
            'url': url_for('viewsession', name=proposal.proposal_space.name, slug=proposal.urlname, _external=True),
            'proposer': proposal.user.fullname,
            'speaker': proposal.speaker.fullname if proposal.speaker else None,
            'email': proposal.email if lastuser.has_permission('siteadmin') else None,
            'phone': proposal.phone if lastuser.has_permission('siteadmin') else None,
            'section': proposal.section.title if proposal.section else None,
            'type': proposal.session_type,
            'level': proposal.technical_level,
            'objective': proposal.objective_html,
            'description': proposal.description_html,
            'requirements': proposal.requirements_html,
            'slides': proposal.slides,
            'links': proposal.links,
            'bio': proposal.bio_html,
            'votes': proposal.votes.count,
            'votes_count': votes_count,
            'votes_groups': votes_groups,
            'votes_bydate': votes_bydate,
            'comments': proposal.comments.count,
            'submitted': proposal.created_at.isoformat() + 'Z',
            'confirmed': proposal.confirmed,
            }


def proposal_data_flat(proposal, groups=[]):
    data = proposal_data(proposal)
    cols = [data[header] for header in proposal_headers if header not in ('votes_groups', 'votes_bydate')]
    for name in groups:
        cols.append(data['votes_groups'][name])
    return cols


@app.route('/<name>/<slug>/json', methods=['GET', 'POST'])
def session_json(name, slug):
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
        return redirect(url_for('viewspace', name=space.name))
    if slug != proposal.urlname:
        return redirect(url_for('session_json', name=space.name, slug=proposal.urlname))
    return jsonp(proposal_data(proposal))


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
        return jsonp(message=comment.message)
    else:
        return jsonp(message='')


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
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname) + "#c%d" % cid)


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
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname) + "#c%d" % cid)


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
    return redirect(url_for('viewsession', name=space.name, slug=proposal.urlname) + "#c%d" % cid)


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
