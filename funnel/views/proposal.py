# -*- coding: utf-8 -*-

import re
from datetime import datetime
from pytz import timezone, utc
from pytz.exceptions import UnknownTimeZoneError

from flask import g, render_template, redirect, request, Markup, abort, flash, escape
from flask.ext.mail import Message
from coaster.views import jsonp, load_models
from coaster.gfm import markdown
from baseframe import _

from .. import app, mail, lastuser
from ..models import db, ProposalSpace, ProposalSpaceSection, Proposal, Comment, Vote, ProposalFeedback, FEEDBACK_AUTH_TYPE
from ..forms import ProposalForm, CommentForm, DeleteCommentForm, ConfirmDeleteForm, ConfirmSessionForm
from coaster.utils import make_name
from coaster.views import requestargs

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


def proposal_data(proposal):
    """
    Return proposal data suitable for a JSON dump. Request helper, not to be used standalone.
    """
    votes_count = None
    votes_groups = None
    votes_bydate = dict([(group.name, {}) for group in proposal.proposal_space.usergroups])

    if 'tz' in request.args:
        try:
            tz = timezone(request.args['tz'])
        except UnknownTimeZoneError:
            abort(400)
    else:
        tz = None

    if lastuser.has_permission('siteadmin'):
        votes_count = len(proposal.votes.votes)
        votes_groups = dict([(group.name, 0) for group in proposal.proposal_space.usergroups])
        groupuserids = dict([(group.name, [user.userid for user in group.users])
            for group in proposal.proposal_space.usergroups])
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


# --- Routes ------------------------------------------------------------------

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
