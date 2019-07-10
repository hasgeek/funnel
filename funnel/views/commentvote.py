# -*- coding: utf-8 -*-

from collections import namedtuple

from flask import abort, flash, g, jsonify, redirect, render_template, request

from baseframe import _, forms
from coaster.auth import current_auth
from coaster.utils import require_one_of, utcnow
from coaster.views import ModelView, UrlForView, jsonp, requires_permission, route

from .. import app, funnelapp, lastuser
from ..forms import CommentForm, DeleteCommentForm
from ..models import Comment, Profile, Project, Proposal, db
from .decorators import legacy_redirect
from .helpers import send_mail
from .mixins import ProposalViewMixin

ProposalComment = namedtuple('ProposalComment', ['proposal', 'comment'])


@route('/<profile>/<project>/proposals/<url_name_suuid>')
class ProposalVoteView(ProposalViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('voteup', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_proposal')
    def voteup(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(current_auth.user, votedown=False)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('votedown', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_proposal')
    def votedown(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(current_auth.user, votedown=True)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('delete_vote', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_proposal')
    def delete_vote(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.cancelvote(current_auth.user)
        db.session.commit()
        message = _("Your vote has been withdrawn")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('comments/new', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('new_comment')
    def new_comment(self):
        to_redirect = self.obj.url_for(_external=True)
        commentform = CommentForm(model=Comment)
        if commentform.validate_on_submit():
            send_mail_info = []
            if commentform.comment_edit_id.data:
                comment = Comment.query.filter_by(suuid=commentform.comment_edit_id.data).first_or_404()
                if comment:
                    if comment.current_permissions.edit_comment:
                        comment.message = commentform.message.data
                        comment.edited_at = utcnow()
                        flash(_("Your comment has been edited"), 'info')
                    else:
                        flash(_("You can only edit your own comments"), 'info')
                else:
                    flash(_("No such comment"), 'error')
            else:
                comment = Comment(user=current_auth.user, commentset=self.obj.commentset,
                    message=commentform.message.data)
                if commentform.parent_id.data:
                    parent = Comment.query.filter_by(suuid=commentform.parent_id.data).first_or_404()
                    if parent.user.email:  # FIXME: https://github.com/hasgeek/funnel/pull/324#discussion_r241270403
                        if parent.user == self.obj.user:  # check if parent comment & proposal owner are same
                            if not current_auth.user == parent.user:  # check if parent comment is by proposal owner
                                send_mail_info.append({'to': self.obj.user.email or self.obj.email,
                                    'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                                    'template': 'proposal_comment_reply_email.md'})
                        else:  # send mail to parent comment owner & proposal owner
                            if not parent.user == current_auth.user:
                                send_mail_info.append({'to': parent.user.email,
                                    'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                                    'template': 'proposal_comment_to_proposer_email.md'})
                            if not self.obj.user == current_auth.user:
                                send_mail_info.append({'to': self.obj.user.email or self.obj.email,
                                    'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                                    'template': 'proposal_comment_email.md'})

                    if parent and parent.commentset == self.obj.commentset:
                        comment.parent = parent
                else:  # for top level comment
                    if not self.obj.user == current_auth.user:
                        send_mail_info.append({'to': self.obj.user.email or self.obj.email,
                            'subject': u"{project} Funnel: {proposal}".format(project=self.obj.project.title, proposal=self.obj.title),
                            'template': 'proposal_comment_email.md'})
                self.obj.commentset.count += 1
                comment.voteset.vote(current_auth.user)  # Vote for your own comment
                db.session.add(comment)
                flash(_("Your comment has been posted"), 'info')
            db.session.commit()
            for item in send_mail_info:
                email_body = render_template(item.pop('template'), proposal=self.obj, comment=comment, link=to_redirect)
                if item.get('to'):
                    # Sender is set to None to prevent revealing email.
                    send_mail(sender=None, body=email_body, **item)
        # Redirect despite this being the same page because HTTP 303 is required to not break
        # the browser Back button
        return redirect(to_redirect, code=303)


@route('/<project>/<url_id_name>', subdomain='<profile>')
class FunnelProposalVoteView(ProposalVoteView):
    pass


ProposalVoteView.init_app(app)
FunnelProposalVoteView.init_app(funnelapp)


class ProposalCommentViewMixin(object):
    model = Proposal
    route_model_map = {'profile': 'project.profile.name',
        'project': 'project.name', 'suuid': '**comment.suuid',
        'url_name_suuid': 'url_name_suuid',
        'url_id_name': 'url_id_name'}

    def loader(self, profile, project, suuid, url_name_suuid=None, url_id_name=None):
        require_one_of(url_name_suuid=url_name_suuid, url_id_name=url_id_name)
        if url_name_suuid:
            proposal = Proposal.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Proposal.url_name_suuid == url_name_suuid
                ).first_or_404()
        else:
            proposal = Proposal.query.join(Project, Profile).filter(
                Profile.name == profile, Project.name == project, Proposal.url_name == url_id_name
                ).first_or_404()

        comment = Comment.query.join(
            Proposal, Comment.commentset_id == Proposal.commentset_id
            ).filter(Comment.suuid == suuid, Proposal.id == proposal.id).first_or_404()

        return ProposalComment(proposal, comment)

    def after_loader(self):
        g.profile = self.obj.proposal.project.profile
        super(ProposalCommentViewMixin, self).after_loader()


@route('/<profile>/<project>/proposals/<url_name_suuid>/comments/<suuid>')
class ProposalCommentView(ProposalCommentViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('json')
    @requires_permission('view')
    def view_comment_json(self):
        return jsonp(message=self.obj.comment.message.text)

    @route('delete', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('delete_comment')
    def delete_comment(self):
        delcommentform = DeleteCommentForm(comment_id=self.obj.comment.id)
        if delcommentform.validate_on_submit():
            self.obj.comment.delete()
            self.obj.proposal.commentset.count -= 1
            db.session.commit()
            flash(_("Your comment was deleted"), 'info')
        else:
            flash(_("Your comment could not be deleted"), 'danger')
        return redirect(self.obj.proposal.url_for(), code=303)

    @route('voteup', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_comment')
    def voteup_comment(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.comment.voteset.vote(current_auth.user, votedown=False)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.proposal.url_for(), code=303)

    @route('votedown', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_comment')
    def votedown_comment(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.comment.voteset.vote(current_auth.user, votedown=True)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.proposal.url_for(), code=303)

    @route('delete_vote', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_comment')
    def delete_comment_vote(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.comment.voteset.cancelvote(current_auth.user)
        db.session.commit()
        message = _("Your vote has been withdrawn")
        if request.is_xhr:
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.proposal.url_for(), code=303)


@route('/<project>/<url_id_name>/comments/<suuid>', subdomain='<profile>')
class FunnelProposalCommentView(ProposalCommentView):
    pass


ProposalCommentView.init_app(app)
FunnelProposalCommentView.init_app(funnelapp)
