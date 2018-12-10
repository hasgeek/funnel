# -*- coding: utf-8 -*-

from datetime import datetime
from flask import redirect, flash, abort, jsonify, request, render_template
from coaster.auth import current_auth
from coaster.views import jsonp, route, requires_permission, UrlForView, ModelView, requestargs
from baseframe import _, forms

from .. import app, funnelapp, lastuser
from ..forms import CommentForm, DeleteCommentForm
from ..models import db, Comment
from .decorators import legacy_redirect
from .helpers import send_mail
from .mixins import ProposalViewMixin, CommentViewMixin


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
        commentform = CommentForm(model=Comment)
        if commentform.validate_on_submit():
            send_mail_info = []
            if commentform.comment_edit_id.data:
                comment = Comment.query.get(int(commentform.comment_edit_id.data))
                if comment:
                    if comment.current_permissions.edit_comment:
                        comment.message = commentform.message.data
                        comment.edited_at = datetime.utcnow()
                        flash(_("Your comment has been edited"), 'info')
                    else:
                        flash(_("You can only edit your own comments"), 'info')
                else:
                    flash(_("No such comment"), 'error')
            else:
                comment = Comment(user=current_auth.user, commentset=self.obj.commentset,
                    message=commentform.message.data)
                if commentform.parent_id.data:
                    parent = Comment.query.get(int(commentform.parent_id.data))
                    if parent.user.email:
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
            to_redirect = self.obj.url_for(_external=True)
            for item in send_mail_info:
                email_body = render_template(item.pop('template'), proposal=self.obj, comment=comment, link=to_redirect)
                if item.get('to'):
                    # Sender is set to None to prevent revealing email.
                    send_mail(sender=None, body=email_body, **item)
        # Redirect despite this being the same page because HTTP 303 is required to not break
        # the browser Back button
        return redirect(to_redirect, code=303)

    @route('comments/delete', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('new_comment')
    @requestargs('comment_id')
    def delete_comment(self, comment_id):
        comment = Comment.query.filter_by(id=comment_id).first_or_404()
        if not comment.current_permissions.delete_comment:
            abort(401)
        delcommentform = DeleteCommentForm(comment_id=comment.id)
        if delcommentform.validate_on_submit():
            comment.delete()
            self.obj.commentset.count -= 1
            db.session.commit()
            flash(_("Your comment was deleted"), 'info')
        else:
            flash(_("Your comment could not be deleted"), 'danger')
        return redirect(self.obj.url_for(), code=303)


@route('/<project>/<url_id_name>', subdomain='<profile>')
class FunnelProposalVoteView(ProposalVoteView):
    pass


ProposalVoteView.init_app(app)
FunnelProposalVoteView.init_app(funnelapp)


@route('/<profile>/<project>/proposals/<url_name_suuid>/comments/<int:comment>')
class CommentView(CommentViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('json')
    @requires_permission('view')
    def json(self):
        return jsonp(message=self.obj.message.text)

    @route('voteup', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_comment')
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
        return redirect(self.proposal.url_for(), code=303)

    @route('votedown', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_comment')
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
        return redirect(self.proposal.url_for(), code=303)

    @route('delete_vote', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('vote_comment')
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
        return redirect(self.proposal.url_for(), code=303)


@route('/<project>/<url_id_name>/comments/<int:comment>', subdomain='<profile>')
class FunnelCommentView(CommentView):
    pass


CommentView.init_app(app)
FunnelCommentView.init_app(funnelapp)
