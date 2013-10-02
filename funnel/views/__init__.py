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
from baseframe import _

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
from coaster.utils import make_name
from coaster.views import requestargs

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
    return render_template('index.html', spaces=spaces, siteadmin=lastuser.has_permission('siteadmin'))


@app.route('/favicon.ico')
def favicon():
    return url_for('static', filename='img/favicon.ico')


@app.route('/login')
@lastuser.login_handler
def login():
    return {'scope': 'id email phone'}


@app.route('/logout')
@lastuser.logout_handler
def logout():
    flash(_("You are now logged out"), category='info')
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


# --- Routes: spaces ----------------------------------------------------------

@app.route('/new', methods=['GET', 'POST'])
@lastuser.requires_permission('siteadmin')
def space_new():
    form = ProposalSpaceForm(model=ProposalSpace)
    if form.validate_on_submit():
        space = ProposalSpace(user=g.user)
        form.populate_obj(space)
        db.session.add(space)
        db.session.commit()
        flash(_("Your new space has been created"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Create a new proposal space"), submit=_("Create space"))


@app.route('/<space>/')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission='view', addlperms=lastuser.permissions)
def space_view(space):
    description = Markup(space.description_html)
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title').all()
    confirmed = Proposal.query.filter_by(proposal_space=space, confirmed=True).order_by(db.desc('created_at')).all()
    unconfirmed = Proposal.query.filter_by(proposal_space=space, confirmed=False).order_by(db.desc('created_at')).all()
    return render_template('space.html', space=space, description=space.description, sections=sections,
        confirmed=confirmed, unconfirmed=unconfirmed, is_siteadmin=lastuser.has_permission('siteadmin'))


@app.route('/<space>/json')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission='view', addlperms=lastuser.permissions)
def space_view_json(space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title').all()
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


@app.route('/<space>/csv')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission='view', addlperms=lastuser.permissions)
def space_view_csv(space):
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


@app.route('/<space>/edit', methods=['GET', 'POST'])
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('edit-space', 'siteadmin'), addlperms=lastuser.permissions)
def space_edit(space):
    form = ProposalSpaceForm(obj=space, model=ProposalSpace)
    if form.validate_on_submit():
        form.populate_obj(space)
        db.session.commit()
        flash(_("Your changes have been saved"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Edit proposal space"), submit=_("Save changes"))


@app.route('/<space>/sections/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('new-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_new(space):
    form = SectionForm(model=ProposalSpaceSection, parent=space)
    if form.validate_on_submit():
        section = ProposalSpaceSection(proposal_space=space)
        form.populate_obj(section)
        db.session.add(section)
        db.session.commit()
        flash(_("Your new section has been added"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("New section"), submit=_("Create section"),
        breadcrumbs=[(space.url_for(), space.title), (space.url_for('sections'), _("Sections"))])


@app.route('/<space>/sections/<section>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission=('edit-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_edit(space, section):
    form = SectionForm(obj=section, model=ProposalSpaceSection, parent=space)
    if form.validate_on_submit():
        form.populate_obj(section)
        db.session.commit()
        flash(_("Your section has been edited"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Edit section"), submit=_("Save changes"),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections")),
            (section.url_for(), section.title)])


@app.route('/<space>/sections/<section>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission=('delete-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_delete(space, section):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        if 'delete' in request.form:
            db.session.delete(section)
            db.session.commit()
            flash(_("Your section has been deleted"), 'info')
        return redirect(space.url_for(), code=303)
    return render_template('delete.html', form=form, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete section ‘{title}’?").format(title=section.title),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections")),
            (section.url_for(), section.title)])



@app.route('/<space>/sections')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_list(space):
    sections = ProposalSpaceSection.query.filter_by(proposal_space=space).all()
    return render_template('sections.html', space=space, sections=sections,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections"))])


@app.route('/<space>/sections/<section>')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (ProposalSpaceSection, {'name': 'section', 'proposal_space': 'space'}, 'section'),
    permission=('view-section', 'siteadmin'), addlperms=lastuser.permissions)
def section_view(space, section):
    return render_template('section.html', space=space, section=section,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('sections'), _("Sections")),
            (section.url_for(), section.title)])


@app.route('/<space>/users')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_list(space):
    return render_template('usergroups.html', space=space, usergroups=space.usergroups,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('usergroups'), _("Users"))])



@app.route('/<space>/users/<group>')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (UserGroup, {'name': 'group', 'proposal_space': 'space'}, 'usergroup'),
    permission=('view-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_view(space, usergroup):
    return render_template('usergroup.html', space=space, usergroup=usergroup,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('usergroups'), _("Users")),
            (usergroup.url_for(), usergroup.title)])


@app.route('/<space>/users/new', defaults={'group': None}, endpoint='usergroup_new', methods=['GET', 'POST'])
@app.route('/<space>/users/<group>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space', kwargs=True,
    permission=('new-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_edit(space, kwargs):
    group = kwargs.get('group')
    form = UserGroupForm(model=UserGroup, parent=space)
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
        return redirect(usergroup.url_for(), code=303)
    if group is None:
        return render_template('baseframe/autoform.html', form=form, title=_("New user group"), submit=_("Create user group"),
            breadcrumbs=[
                (space.url_for(), space.title),
                (space.url_for('usergroups'), _("Users"))])

    else:
        return render_template('baseframe/autoform.html', form=form, title=_("Edit user group"), submit=_("Save changes"),
            breadcrumbs=[
                (space.url_for(), space.title),
                (space.url_for('usergroups'), _("Users")),
                (usergroup.url_for(), usergroup.title)])


@app.route('/<space>/users/<group>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (UserGroup, {'name': 'group', 'proposal_space': 'space'}, 'usergroup'),
    permission=('delete-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_delete(space, usergroup):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        if 'delete' in request.form:
            db.session.delete(usergroup)
            db.session.commit()
            flash(_("Your user group has been deleted"), 'info')
            return redirect(space.url_for('usergroups'))
        else:
            return redirect(usergroup.url_for())
    return render_template('delete.html', form=form, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete user group ‘{title}’?").format(title=usergroup.title),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('usergroups'), _("Users")),
            (usergroup.url_for(), usergroup.title)])


@app.route('/<space>/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    permission='new-proposal', addlperms=lastuser.permissions)
def proposal_new(space):
    form = ProposalForm(model=Proposal, parent=space)
    del form.session_type  # We don't use this anymore
    form.section.query = ProposalSpaceSection.query.filter_by(proposal_space=space, public=True).order_by('title')
    if len(list(form.section.query.all())) == 0:
        # Don't bother with sections when there aren't any
        del form.section
    if request.method == 'GET':
        form.email.data = g.user.email
        form.phone.data = g.user.phone
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
        flash(_("Your new session has been saved"), 'info')
        return redirect(proposal.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Submit a session proposal"),
        submit=_("Submit proposal"),
        breadcrumbs=[(space.url_for(), space.title)],
        message=Markup(
            _('This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.')))


@app.route('/<space>/<proposal>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission=('edit-proposal', 'siteadmin'), addlperms=lastuser.permissions)
def proposal_edit(space, proposal):
    form = ProposalForm(obj=proposal, model=Proposal, parent=space)
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
        flash(_("Your changes have been saved"), 'info')
        return redirect(proposal.url_for(), code=303)
    return render_template('baseframe/autoform.html', form=form, title=_("Edit session proposal"), submit=_("Save changes"),
        breadcrumbs=[(space.url_for(), space.title),
                     (proposal.url_for(), proposal.title)],
        message=Markup(
            _('This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.')))


@app.route('/<space>/<proposal>/confirm', methods=['POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission=('confirm-proposal', 'siteadmin'), addlperms=lastuser.permissions)
def proposal_confirm(space, proposal):
    form = ConfirmSessionForm()
    if form.validate_on_submit():
        proposal.confirmed = not proposal.confirmed
        db.session.commit()
        if proposal.confirmed:
            flash(_("This proposal has been confirmed."), 'success')
        else:
            flash(_("This session has been cancelled."), 'success')
    return redirect(proposal.url_for())


@app.route('/<space>/<proposal>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission=('delete-proposal', 'siteadmin'), addlperms=lastuser.permissions)
def proposal_delete(space, proposal):
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
            flash(_("Your proposal has been deleted"), "info")
            return redirect(space.url_for())
        else:
            return redirect(proposal.url_for())
    return render_template('delete.html', form=form, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete your proposal ‘{title}’? "
                u"This will remove all votes and comments as well. This operation "
                u"is permanent and cannot be undone.").format(title=proposal.title))


def urllink(m):
    s = m.group(0)
    if not (s.startswith('http://') or s.startswith('https://')):
        s = 'http://' + s
    return '<a href="%s" rel="nofollow" target="_blank">%s</a>' % (s, s)


def send_mail(sender, to, body, subject):
    msg = Message(sender=sender, subject=subject, recipients=[to])
    msg.body = body
    msg.html = markdown(msg.body)  # FIXME: This does not include HTML head/body tags
    mail.send(msg)


@app.route('/<space>/<proposal>', methods=['GET', 'POST'])
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='view', addlperms=lastuser.permissions)
def proposal_view(space, proposal):
    if proposal.proposal_space != space:
        return redirect(proposal.url_for(), code=301)

    comments = sorted(Comment.query.filter_by(commentspace=proposal.comments, parent=None).order_by('created_at').all(),
        key=lambda c: c.votes.count, reverse=True)
    commentform = CommentForm(model=Comment)
    delcommentform = DeleteCommentForm()
    if request.method == 'POST':
        if request.form.get('form.id') == 'newcomment' and commentform.validate() and 'new-comment' in g.permissions:
            send_mail_info = []
            if commentform.comment_edit_id.data:
                comment = Comment.query.get(int(commentform.comment_edit_id.data))
                if comment:
                    if 'edit-comment' in comment.permissions(g.user, g.permissions):
                        comment.message = commentform.message.data
                        comment.edited_at = datetime.utcnow()
                        flash(_("Your comment has been edited"), 'info')
                    else:
                        flash(_("You can only edit your own comments"), 'info')
                else:
                    flash(_("No such comment"), 'error')
            else:
                comment = Comment(user=g.user, commentspace=proposal.comments,
                    message=commentform.message.data)
                if commentform.parent_id.data:
                    parent = Comment.query.get(int(commentform.parent_id.data))
                    if parent.user.email:
                        if parent.user == proposal.user:  # check if parent comment & proposal owner are same
                            if not g.user == parent.user:  # check if parent comment is by proposal owner
                                send_mail_info.append({'to': proposal.user.email or proposal.email,
                                    'subject': u"{space} Funnel: {proposal}".format(space=space.title, proposal=proposal.title),
                                    'template': 'proposal_comment_reply_email.md'})
                        else:  # send mail to parent comment owner & proposal owner
                            if not parent.user == g.user:
                                send_mail_info.append({'to': parent.user.email,
                                    'subject': u"{space} Funnel: {proposal}".format(space=space.title, proposal=proposal.title),
                                    'template': 'proposal_comment_to_proposer_email.md'})
                            if not proposal.user == g.user:
                                send_mail_info.append({'to': proposal.user.email or proposal.email,
                                    'subject': u"{space} Funnel: {proposal}".format(space=space.title, proposal=proposal.title),
                                    'template': 'proposal_comment_email.md'})

                    if parent and parent.commentspace == proposal.comments:
                        comment.parent = parent
                else:  # for top level comment
                    if not proposal.user == g.user:
                        send_mail_info.append({'to': proposal.user.email or proposal.email,
                            'subject': u"{space} Funnel: {proposal}".format(space=space.title, proposal=proposal.title),
                            'template': 'proposal_comment_email.md'})
                proposal.comments.count += 1
                comment.votes.vote(g.user)  # Vote for your own comment
                db.session.add(comment)
                flash(_("Your comment has been posted"), 'info')
            db.session.commit()
            to_redirect = comment.url_for(proposal=proposal, _external=True)
            for item in send_mail_info:
                email_body = render_template(item.pop('template'), proposal=proposal, comment=comment, link=to_redirect)
                send_mail(sender=None, body=email_body, **item)
            # Redirect despite this being the same page because HTTP 303 is required to not break
            # the browser Back button
            return redirect(to_redirect, code=303)
        elif request.form.get('form.id') == 'delcomment' and delcommentform.validate():
            comment = Comment.query.get(int(delcommentform.comment_id.data))
            if comment:
                if 'delete-comment' in comment.permissions(g.user, g.permissions):
                    comment.delete()
                    proposal.comments.count -= 1
                    db.session.commit()
                    flash(_("Your comment was deleted"), 'info')
                else:
                    flash(_("You did not post that comment"), 'error')
            else:
                flash(_("No such comment"), 'error')
            return redirect(proposal.url_for(), code=303)
    links = [Markup(url_re.sub(urllink, unicode(escape(l)))) for l in proposal.links.replace('\r\n', '\n').split('\n') if l]
    confirmform = ConfirmSessionForm()
    return render_template('proposal.html', space=space, proposal=proposal,
        comments=comments, commentform=commentform, delcommentform=delcommentform,
        breadcrumbs=[(space.url_for(), space.title)],
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
            'name': proposal.url_name,
            'title': proposal.title,
            'url': proposal.url_for(_external=True),
            'proposer': proposal.user.fullname,
            'speaker': proposal.speaker.fullname if proposal.speaker else None,
            'email': proposal.email if lastuser.has_permission('siteadmin') else None,
            'phone': proposal.phone if lastuser.has_permission('siteadmin') else None,
            'section': proposal.section.title if proposal.section else None,
            'type': proposal.session_type,
            'level': proposal.technical_level,
            'objective': proposal.objective.html,
            'description': proposal.description.html,
            'requirements': proposal.requirements.html,
            'slides': proposal.slides,
            'links': proposal.links,
            'bio': proposal.bio.html,
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


@app.route('/<space>/<proposal>/feedback', methods=['POST'])
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='view', addlperms=lastuser.permissions)
@requestargs('id_type', 'userid', ('content', int), ('presentation', int), ('min_scale', int), ('max_scale', int))
def session_feedback(space, proposal, id_type, userid, content, presentation, min_scale=0, max_scale=2):
    # Process feedback
    if not min_scale <= content <= max_scale:
        abort(400)
    if not min_scale <= presentation <= max_scale:
        abort(400)
    if id_type != 'email':
        abort(400)

    # Was feedback already submitted?
    feedback = ProposalFeedback.query.filter_by(
        proposal=proposal,
        auth_type=FEEDBACK_AUTH_TYPE.NOAUTH,
        id_type=id_type,
        userid=userid).first()
    if feedback is not None:
        return "Dupe\n", 403
    else:
        feedback = ProposalFeedback(
            proposal=proposal,
            auth_type=FEEDBACK_AUTH_TYPE.NOAUTH,
            id_type=id_type,
            userid=userid,
            min_scale=min_scale,
            max_scale=max_scale,
            content=content,
            presentation=presentation)
        db.session.add(feedback)
        db.session.commit()
        return "Saved\n", 201


@app.route('/<space>/<proposal>/json', methods=['GET', 'POST'])
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='view', addlperms=lastuser.permissions)
def proposal_json(space, proposal):
    return jsonp(proposal_data(proposal))


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


@app.route('/<space>/<proposal>/next')
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='view', addlperms=lastuser.permissions)
def proposal_next(space, proposal):
    next = proposal.getnext()
    if next:
        return redirect(next.url_for())
    else:
        flash(_("You were at the last proposal"), 'info')
        return redirect(space.url_for())


@app.route('/<space>/<proposal>/prev')
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='view', addlperms=lastuser.permissions)
def proposal_prev(space, proposal):
    prev = proposal.getprev()
    if prev:
        return redirect(prev.url_for())
    else:
        flash(_("You were at the first proposal"), 'info')
        return redirect(space.url_for())
