from collections import namedtuple

from flask import abort, flash, jsonify, redirect

from baseframe import _, forms, request_is_xhr
from coaster.auth import current_auth
from coaster.views import (
    ModelView,
    UrlForView,
    requires_permission,
    requires_roles,
    route,
)

from .. import app, funnelapp
from ..forms import CommentDeleteForm, CommentForm
from ..models import Comment, Commentset, Proposal, db
from .decorators import legacy_redirect
from .helpers import requires_login
from .mixins import ProposalViewMixin

ProposalComment = namedtuple('ProposalComment', ['proposal', 'comment'])


@Proposal.views('vote')
@route('/<profile>/<project>/proposals/<url_name_uuid_b58>')
class ProposalVoteView(ProposalViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('voteup', methods=['POST'])
    @requires_login
    @requires_permission('vote_proposal')
    def voteup(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(current_auth.user, votedown=False)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request_is_xhr():
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('votedown', methods=['POST'])
    @requires_login
    @requires_permission('vote_proposal')
    def votedown(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(current_auth.user, votedown=True)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request_is_xhr():
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('delete_vote', methods=['POST'])
    @requires_login
    @requires_permission('vote_proposal')
    def delete_vote(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.cancelvote(current_auth.user)
        db.session.commit()
        message = _("Your vote has been withdrawn")
        if request_is_xhr():
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)


@route('/<project>/<url_id_name>', subdomain='<profile>')
class FunnelProposalVoteView(ProposalVoteView):
    pass


ProposalVoteView.init_app(app)
FunnelProposalVoteView.init_app(funnelapp)


@route('/comments/<commentset>')
class CommentsetView(UrlForView, ModelView):
    model = Commentset
    route_model_map = {'commentset': 'uuid_b58'}

    def loader(self, commentset, profile=None):
        # `profile` remains for funnelapp even though it's not used.
        return Commentset.query.filter(Commentset.uuid_b58 == commentset).one_or_404()

    @route('new', methods=['POST'])
    @requires_login
    @requires_roles({'parent_participant'})
    def new_comment(self):
        # TODO: Make this endpoint support AJAX.

        if self.obj.parent is None:
            return redirect('/')

        commentform = CommentForm(model=Comment)
        if commentform.validate_on_submit():
            comment = Comment(
                user=current_auth.user,
                commentset=self.obj,
                message=commentform.message.data,
            )
            if commentform.parent_id.data:
                parent_comment = Comment.query.filter_by(
                    uuid_b58=commentform.parent_id.data
                ).first_or_404()
                if parent_comment and self.obj == parent_comment.commentset:
                    comment.parent = parent_comment
            self.obj.count = Commentset.count + 1
            comment.voteset.vote(current_auth.user)  # Vote for your own comment
            db.session.add(comment)
            db.session.commit()
            flash(_("Your comment has been posted"), 'info')
            return redirect(comment.url_for(), code=303)
        else:
            for error in commentform.get_verbose_errors():
                flash(error, category='error')
        # Redirect despite this being the same page because HTTP 303 is required
        # to not break the browser Back button.
        return redirect(self.obj.views.url(), code=303)


@route('/comments/<commentset>', subdomain='<profile>')
class FunnelCommentsetView(CommentsetView):
    pass


CommentsetView.init_app(app)
FunnelCommentsetView.init_app(funnelapp)


@route('/comments/<commentset>/<comment>')
class CommentView(UrlForView, ModelView):
    model = Comment
    route_model_map = {'commentset': 'commentset.uuid_b58', 'comment': 'uuid_b58'}

    def loader(self, commentset, comment, profile=None):
        comment = (
            Comment.query.join(Commentset)
            .filter(Commentset.uuid_b58 == commentset, Comment.uuid_b58 == comment)
            .one_or_404()
        )
        return comment

    @route('')
    @requires_roles({'reader'})
    def view(self):
        return redirect(self.obj.views.url(), code=303)

    @route('json')
    @requires_roles({'reader'})
    def view_json(self):
        return jsonify(status=True, message=self.obj.message.text)

    @route('edit', methods=['POST'])
    @requires_login
    @requires_roles({'author'})
    def edit(self):
        commentform = CommentForm(model=Comment)
        if commentform.validate_on_submit():
            if self.obj.current_roles.author:
                self.obj.message = commentform.message.data
                self.obj.edited_at = db.func.utcnow()
                flash(_("Your comment has been edited"), 'info')
            else:
                flash(_("You can only edit your own comments"), 'info')
            db.session.commit()
        else:
            for error in commentform.get_verbose_errors():
                flash(error, category='error')
        # Redirect despite this being the same page because HTTP 303 is required
        # to not break the browser Back button.
        return redirect(self.obj.url_for(), code=303)

    @route('delete', methods=['POST'])
    @requires_login
    @requires_roles({'author'})
    def delete(self):
        commentset = self.obj.commentset
        delcommentform = CommentDeleteForm(comment_id=self.obj.id)
        if delcommentform.validate_on_submit():
            self.obj.delete()
            commentset.count = Commentset.count - 1
            db.session.commit()
            flash(_("Your comment was deleted"), 'info')
        else:
            flash(_("Your comment could not be deleted"), 'danger')
        return redirect(commentset.views.url(), code=303)

    @route('voteup', methods=['POST'])
    @requires_login
    @requires_roles({'reader'})
    def voteup(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(current_auth.user, votedown=False)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request_is_xhr():
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('votedown', methods=['POST'])
    @requires_login
    @requires_roles({'reader'})
    def votedown(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.vote(current_auth.user, votedown=True)
        db.session.commit()
        message = _("Your vote has been recorded")
        if request_is_xhr():
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('delete_vote', methods=['POST'])
    @requires_login
    @requires_roles({'reader'})
    def delete_vote(self):
        csrf_form = forms.Form()
        if not csrf_form.validate_on_submit():
            abort(403)
        self.obj.voteset.cancelvote(current_auth.user)
        db.session.commit()
        message = _("Your vote has been withdrawn")
        if request_is_xhr():
            return jsonify(message=message, code=200)
        flash(message, 'info')
        return redirect(self.obj.url_for(), code=303)

    @route('report_spam', methods=['POST'])
    @requires_login
    def report_spam(self):
        csrf_form = forms.Form()
        if not (
            current_auth.user.is_comment_moderator and csrf_form.validate_on_submit()
        ):
            abort(403)

        self.obj.report_spam(actor=current_auth.user)
        flash(
            _("The comment has been reported as spam"), 'info',
        )
        return redirect(self.obj.commentset.views.url(), code=303)


@route('/comments/<commentset>/<comment>', subdomain='<profile>')
class FunnelCommentView(CommentView):
    pass


CommentView.init_app(app)
FunnelCommentView.init_app(funnelapp)
