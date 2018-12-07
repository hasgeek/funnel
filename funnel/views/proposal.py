# -*- coding: utf-8 -*-

from datetime import datetime
from bleach import linkify

from flask import g, render_template, redirect, request, Markup, abort, flash, escape
from flask_mail import Message
from sqlalchemy import or_
from coaster.utils import make_name
from coaster.views import jsonp, load_models, requestargs, requires_permission, route, render_with, UrlForView, ModelView
from coaster.gfm import markdown
from coaster.auth import current_auth
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla, Form

from .. import app, funnelapp, mail, lastuser
from ..models import (db, Profile, Project, ProjectRedirect, Section, Proposal,
    ProposalRedirect, Comment, ProposalFeedback, FEEDBACK_AUTH_TYPE)
from ..forms import ProposalForm, CommentForm, DeleteCommentForm, ProposalTransitionForm, ProposalMoveForm
from .mixins import ProjectViewMixin, ProposalViewMixin


proposal_headers = [
    'id',
    'title',
    'url',
    'fullname',
    'proposer',
    'speaker',
    'email',
    'slides',
    'preview_video',
    'phone',
    'section',
    'type',
    'level',
    'votes',
    'comments',
    'submitted',
    'confirmed'
    ]


def send_mail(sender, to, body, subject):
    msg = Message(sender=sender, subject=subject, recipients=[to])
    msg.body = body
    msg.html = markdown(msg.body)  # FIXME: This does not include HTML head/body tags
    mail.send(msg)


def proposal_data(proposal):
    """
    Return proposal data suitable for a JSON dump. Request helper, not to be used standalone.
    """
    return dict([
            ('id', proposal.id),
            ('name', proposal.url_name),
            ('title', proposal.title),
            ('url', proposal.url_for(_external=True)),
            ('json_url', proposal.url_for('json', _external=True)),
            ('fullname', proposal.owner.fullname),
            ('proposer', proposal.user.pickername),
            ('speaker', proposal.speaker.pickername if proposal.speaker else None),
            ('section', proposal.section.title if proposal.section else None),
            ('type', proposal.session_type),
            ('level', proposal.technical_level),
            ('objective', proposal.objective.html),
            ('description', proposal.description.html),
            ('requirements', proposal.requirements.html),
            ('slides', proposal.slides),
            ('links', proposal.links),
            ('preview_video', proposal.preview_video),
            ('bio', proposal.bio.html),
            ('votes', proposal.voteset.count),
            ('comments', proposal.commentset.count),
            ('submitted', proposal.created_at.isoformat() + 'Z'),
            ('confirmed', bool(proposal.state.CONFIRMED)),
        ] + ([
            ('email', proposal.email),
            ('phone', proposal.phone),
            ('location', proposal.location),
            ('votes_count', proposal.votes_count()),
            ('votes_groups', proposal.votes_by_group()),
            ('votes_bydate', proposal.votes_by_date()),
            ('status', proposal.state.value),
            ('state', proposal.state.label.name),
        ] if 'view-contactinfo' in current_auth.permissions else []))


def proposal_data_flat(proposal, groups=[]):
    data = proposal_data(proposal)
    cols = [data.get(header) for header in proposal_headers if header not in ('votes_groups', 'votes_bydate')]
    for name in groups:
        cols.append(data['votes_groups'][name])
    cols.append(proposal.state.label.name)
    return cols


# --- Routes ------------------------------------------------------------------
@route('/<profile>/<project>')
class ProjectProposalView(ProjectViewMixin, UrlForView, ModelView):
    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-proposal')
    def new_proposal(self):
        form = ProposalForm(model=Proposal, parent=self.obj)
        del form.session_type  # We don't use this anymore
        if self.obj.inherit_sections:
            form.section.query = Section.query.filter(or_(Section.project == self.obj, Section.project == self.obj.parent_project), Section.public == True).order_by('title')
        else:
            form.section.query = Section.query.filter(Section.project == self.obj, Section.public == True).order_by('title')
        if len(list(form.section.query.all())) == 0:
            # Don't bother with sections when there aren't any
            del form.section
        if request.method == 'GET':
            form.email.data = g.user.email
            form.phone.data = g.user.phone
        if form.validate_on_submit():
            proposal = Proposal(user=current_auth.user, project=self.obj)
            with db.session.no_autoflush:
                proposal.voteset.vote(g.user)  # Vote up your own proposal by default
            form.populate_obj(proposal.formdata)
            proposal.name = make_name(proposal.title)
            db.session.add(proposal)
            db.session.commit()
            flash(_("Your new session has been saved"), 'info')
            return redirect(proposal.url_for(), code=303)
        return render_form(form=form, title=_("Submit a session proposal"),
            submit=_("Submit proposal"),
            message=self.obj.instructions or Markup(
                _('This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.')))


@route('/<project>', subdomain='<profile>')
class FunnelProjectProposalView(ProjectProposalView):
    pass


ProjectProposalView.init_app(app)
FunnelProjectProposalView.init_app(funnelapp)


@route('/<profile>/<project>/<proposal>')
class ProposalView(ProposalViewMixin, UrlForView, ModelView):
    @route('')
    @render_with('proposal.html.jinja2')
    @requires_permission('view')
    def view(self):
        comments = sorted(Comment.query.filter_by(commentset=self.obj.commentset, parent=None).order_by('created_at').all(),
            key=lambda c: c.voteset.count, reverse=True)
        commentform = CommentForm(model=Comment)
        delcommentform = DeleteCommentForm()
        # TODO: Remove comment methods to a separate view
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
                    comment = Comment(user=g.user, commentset=self.obj.commentset,
                        message=commentform.message.data)
                    if commentform.parent_id.data:
                        parent = Comment.query.get(int(commentform.parent_id.data))
                        if parent.user.email:
                            if parent.user == self.obj.user:  # check if parent comment & proposal owner are same
                                if not g.user == parent.user:  # check if parent comment is by proposal owner
                                    send_mail_info.append({'to': self.obj.user.email or self.obj.email,
                                        'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                                        'template': 'proposal_comment_reply_email.md'})
                            else:  # send mail to parent comment owner & proposal owner
                                if not parent.user == g.user:
                                    send_mail_info.append({'to': parent.user.email,
                                        'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                                        'template': 'proposal_comment_to_proposer_email.md'})
                                if not self.obj.user == g.user:
                                    send_mail_info.append({'to': self.obj.user.email or self.obj.email,
                                        'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                                        'template': 'proposal_comment_email.md'})

                        if parent and parent.commentset == self.obj.commentset:
                            comment.parent = parent
                    else:  # for top level comment
                        if not self.obj.user == g.user:
                            send_mail_info.append({'to': self.obj.user.email or self.obj.email,
                                'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                                'template': 'proposal_comment_email.md'})
                    self.obj.commentset.count += 1
                    comment.voteset.vote(g.user)  # Vote for your own comment
                    db.session.add(comment)
                    flash(_("Your comment has been posted"), 'info')
                db.session.commit()
                to_redirect = comment.url_for(proposal=self.obj, _external=True)
                for item in send_mail_info:
                    email_body = render_template(item.pop('template'), proposal=self.obj, comment=comment, link=to_redirect)
                    if item.get('to'):
                        # Sender is set to None to prevent revealing email.
                        send_mail(sender=None, body=email_body, **item)
                # Redirect despite this being the same page because HTTP 303 is required to not break
                # the browser Back button
                return redirect(to_redirect, code=303)
            elif request.form.get('form.id') == 'delcomment' and delcommentform.validate():
                comment = Comment.query.get(int(delcommentform.comment_id.data))
                if comment:
                    if 'delete-comment' in comment.permissions(g.user, g.permissions):
                        comment.delete()
                        self.obj.commentset.count -= 1
                        db.session.commit()
                        flash(_("Your comment was deleted"), 'info')
                    else:
                        flash(_("You did not post that comment"), 'error')
                else:
                    flash(_("No such comment"), 'error')
                return redirect(self.obj.url_for(), code=303)
        links = [Markup(linkify(unicode(escape(l)))) for l in self.obj.links.replace('\r\n', '\n').split('\n') if l]

        transition_form = ProposalTransitionForm(obj=self.obj)

        proposal_move_form = None
        if 'move_to' in self.obj.current_access():
            proposal_move_form = ProposalMoveForm()

        return dict(project=self.obj.project, proposal=self.obj,
            comments=comments, commentform=commentform, delcommentform=delcommentform,
            votes_groups=self.obj.votes_by_group(),
            links=links, transition_form=transition_form, proposal_move_form=proposal_move_form,
            part_a=self.obj.project.proposal_part_a.get('title', 'Objective'),
            part_b=self.obj.project.proposal_part_b.get('title', 'Description'), csrf_form=Form())

    @route('json')
    @requires_permission('view')
    def json(self):
        return jsonp(proposal_data(self.obj))

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit-proposal')
    def edit(self):
        form = ProposalForm(obj=self.obj.formdata, model=Proposal, parent=self.obj.project)
        if not self.obj.session_type:
            del form.session_type  # Remove this if we're editing a proposal that had no session type
        if self.obj.project.inherit_sections:
            form.section.query = Section.query.filter(or_(Section.project == self.obj.project, Section.project == self.obj.project.parent_project), Section.public == True).order_by('title')
        else:
            form.section.query = Section.query.filter(Section.project == self.obj.project, Section.public == True).order_by('title')
        if len(list(form.section.query.all())) == 0:
            # Don't bother with sections when there aren't any
            del form.section
        if self.obj.user != g.user:
            del form.speaking
        if form.validate_on_submit():
            form.populate_obj(self.obj.formdata)
            self.obj.name = make_name(self.obj.title)
            self.obj.edited_at = datetime.utcnow()
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for(), code=303)
        return render_form(form=form, title=_("Edit session proposal"), submit=_("Save changes"),
            message=self.obj.project.instructions or Markup(
                _('This form uses <a href="http://daringfireball.net/projects/markdown/">Markdown</a> for formatting.')))

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('delete-proposal')
    def delete(self):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete your proposal ‘{title}’? "
                    u"This will remove all votes and comments as well. This operation "
                    u"is permanent and cannot be undone.").format(title=self.obj.title),
            success=_("Your proposal has been deleted"),
            next=self.obj.project.url_for(),
            cancel_url=self.obj.url_for())

    @route('transition', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('confirm-proposal')
    def transition(self):
        transition_form = ProposalTransitionForm(obj=self.obj)
        if transition_form.validate_on_submit():  # check if the provided transition is valid
            transition = getattr(self.obj.current_access(), transition_form.transition.data)
            transition()  # call the transition
            db.session.commit()
            flash(transition.data['message'], 'success')
        else:
            flash(_("Invalid transition for this proposal."), 'error')
            abort(403)
        return redirect(self.obj.url_for())

    @route('next')
    @requires_permission('view')
    def next(self):
        next = self.obj.getnext()
        if next:
            return redirect(next.url_for())
        else:
            flash(_("You were at the last proposal"), 'info')
            return redirect(self.obj.project.url_for())

    @route('prev')
    @requires_permission('view')
    def prev(self):
        prev = self.obj.getprev()
        if prev:
            return redirect(prev.url_for())
        else:
            flash(_("You were at the first proposal"), 'info')
            return redirect(self.obj.project.url_for())

    @route('move', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('move-proposal')
    def moveto(self):
        proposal_move_form = ProposalMoveForm()
        if proposal_move_form.validate_on_submit():
            target_project = proposal_move_form.target.data
            if target_project != self.obj.project:
                self.obj.current_access().move_to(target_project)
                db.session.commit()
            flash(_("The proposal has been successfully moved to {project}.".format(project=target_project.title)))
        else:
            flash(_("Please choose a project you want to move this proposal to."))
        return redirect(self.obj.url_for(), 303)


@route('/<project>/<proposal>', subdomain='<profile>')
class FunnelProposalView(ProposalView):
    pass


ProposalView.init_app(app)
FunnelProposalView.init_app(funnelapp)


@app.route('/<profile>/<project>/<proposal>/feedback', methods=['POST'])
@funnelapp.route('/<project>/<proposal>/feedback', methods=['POST'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    permission='view', addlperms=lastuser.permissions)
@requestargs('id_type', 'userid', ('content', int), ('presentation', int), ('min_scale', int), ('max_scale', int))
def session_feedback(profile, project, proposal, id_type, userid, content, presentation, min_scale=0, max_scale=2):
    # Process feedback
    if not min_scale <= content <= max_scale:
        abort(400)
    if not min_scale <= presentation <= max_scale:
        abort(400)
    if id_type not in ('email', 'deviceid'):
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
