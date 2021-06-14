from collections import namedtuple

from flask import flash, jsonify, redirect, request

from baseframe import _, forms
from baseframe.forms import Form, render_form
from coaster.auth import current_auth
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app
from ..forms import CommentForm
from ..models import (
    Comment,
    CommentModeratorReport,
    CommentReplyNotification,
    CommentReportReceivedNotification,
    Commentset,
    NewCommentNotification,
    db,
)
from .login_session import requires_login
from .notification import dispatch_notification

ProposalComment = namedtuple('ProposalComment', ['proposal', 'comment'])


@Comment.views('url')
def comment_url(obj):
    url = None
    commentset_url = obj.commentset.views.url()
    if commentset_url is not None:
        url = commentset_url + '#c-' + obj.uuid_b58
    return url


@Commentset.views('json_comments')
def commentset_json(obj):
    toplevel_comments = obj.toplevel_comments.order_by(Comment.created_at.desc())
    return [
        comment.current_access(datasets=('json', 'related'))
        for comment in toplevel_comments
        if comment.state.PUBLIC or comment.replies
    ]


@Commentset.views('url')
def parent_comments_url(obj):
    url = None  # project or proposal object
    if obj.project is not None:
        url = obj.project.url_for('comments', _external=True)
    elif obj.proposal is not None:
        url = obj.proposal.url_for(_external=True)
    return url


@route('/comments/<commentset>')
class CommentsetView(UrlForView, ModelView):
    model = Commentset
    route_model_map = {'commentset': 'uuid_b58'}

    def loader(self, commentset):
        return Commentset.query.filter(Commentset.uuid_b58 == commentset).one_or_404()

    @route('', methods=['GET'])
    def view(self):
        return redirect(self.obj.views.url(), code=303)

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @render_with(json=True)
    def new_comment(self):
        if self.obj.parent is None:
            return redirect('/')

        commentform = CommentForm()
        if commentform.validate_on_submit():
            comment = Comment(
                user=current_auth.user,
                commentset=self.obj,
                message=commentform.message.data,
            )

            self.obj.count = Commentset.count + 1
            db.session.add(comment)

            if not self.obj.current_roles.document_subscriber:
                self.obj.add_subscriber(actor=current_auth.user, user=current_auth.user)

            db.session.commit()
            dispatch_notification(
                NewCommentNotification(document=comment.commentset, fragment=comment)
            )
            return {
                'status': 'ok',
                'message': _("Your comment has been posted"),
                'comments': self.obj.views.json_comments(),
                'comment': comment.current_access(datasets=('json', 'related')),
            }
        commentform_html = render_form(
            form=commentform,
            title='',
            submit=_("Post comment"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': commentform_html}

    @route('subscribe', methods=['POST'])
    @requires_login
    @render_with(json=True)
    def subscribe(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            self.obj.add_subscriber(actor=current_auth.user, user=current_auth.user)
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("Subscribed to this comment thread"),
            }
        return {
            'status': 'error',
            'error_code': 'subscribe_error',
            'error_description': _("This page timed out. Reload and try again"),
            'error_details': csrf_form.errors,
        }, 422

    @route('unsubscribe', methods=['POST'])
    @requires_login
    @render_with(json=True)
    def unsubscribe(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            self.obj.remove_subscriber(actor=current_auth.user, user=current_auth.user)
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("Unsubscribed from this comment thread"),
            }
        return {
            'status': 'error',
            'error_code': 'unsubscribe_error',
            'error_description': _("This page timed out. Reload and try again"),
            'error_details': csrf_form.errors,
        }, 422

    @route('seen', methods=['POST'])
    @requires_login
    @render_with(json=True)
    def update_last_seen_at(self):
        csrf_form = forms.Form()
        if csrf_form.validate_on_submit():
            self.obj.update_last_seen_at(user=current_auth.user)
            db.session.commit()
            return {'status': 'ok'}
        return {
            'status': 'error',
            'error_code': 'update_seen_at_error',
            'error_description': _("This page timed out. Reload and try again"),
            'error_details': csrf_form.errors,
        }, 422


CommentsetView.init_app(app)


@route('/comments/<commentset>/<comment>')
class CommentView(UrlForView, ModelView):
    model = Comment
    route_model_map = {'commentset': 'commentset.uuid_b58', 'comment': 'uuid_b58'}

    def loader(self, commentset, comment):
        comment = (
            Comment.query.join(Commentset)
            .filter(Commentset.uuid_b58 == commentset, Comment.uuid_b58 == comment)
            .one_or_none()
        )
        if comment is None:
            # if the comment doesn't exist or deleted, return the commentset,
            # `after_loader()` will redirect to the commentset instead.
            return Commentset.query.filter(
                Commentset.uuid_b58 == commentset
            ).one_or_404()
        return comment

    def after_loader(self):
        if isinstance(self.obj, Commentset):
            flash(
                _("That comment could not be found. It may have been deleted"), 'error'
            )
            return redirect(self.obj.url_for(), code=303)
        return super().after_loader()

    @route('')
    @requires_roles({'reader'})
    def view(self):
        return redirect(self.obj.views.url(), code=303)

    @route('json')
    @requires_roles({'reader'})
    def view_json(self):
        return jsonify(status=True, message=self.obj.message.text)

    @route('reply', methods=['GET', 'POST'])
    @requires_roles({'reader'})
    def reply(self):
        commentform = CommentForm()

        if commentform.validate_on_submit():
            comment = Comment(
                in_reply_to=self.obj,
                user=current_auth.user,
                commentset=self.obj.commentset,
                message=commentform.message.data,
            )

            self.obj.commentset.count = Commentset.count + 1
            db.session.add(comment)
            db.session.commit()
            dispatch_notification(
                CommentReplyNotification(
                    document=comment.in_reply_to, fragment=comment
                ),
                NewCommentNotification(document=comment.commentset, fragment=comment),
            )
            return {
                'status': 'ok',
                'message': _("Your comment has been posted"),
                'comments': self.obj.commentset.views.json_comments(),
                'comment': comment.current_access(datasets=('json', 'related')),
            }

        commentform_html = render_form(
            form=commentform,
            title='',
            submit=_("Post comment"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': commentform_html}

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @render_with(json=True)
    @requires_roles({'author'})
    def edit(self):
        commentform = CommentForm(obj=self.obj)
        if commentform.validate_on_submit():
            self.obj.message = commentform.message.data
            self.obj.edited_at = db.func.utcnow()
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("Your comment has been edited"),
                'comments': self.obj.commentset.views.json_comments(),
                'comment': self.obj.current_access(datasets=('json', 'related')),
            }
        commentform_html = render_form(
            form=commentform,
            title='',
            submit=_("Edit comment"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': commentform_html}

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @render_with(json=True)
    @requires_roles({'author'})
    def delete(self):
        delcommentform = Form()

        if delcommentform.validate_on_submit():
            commentset = self.obj.commentset
            self.obj.delete()
            commentset.count = Commentset.count - 1
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("Your comment has been deleted"),
                'comments': self.obj.commentset.views.json_comments(),
            }

        delcommentform_html = render_form(
            form=delcommentform,
            title='Delete this comment?',
            submit=_("Delete"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': delcommentform_html}

    @route('report_spam', methods=['GET', 'POST'])
    @requires_login
    def report_spam(self):
        csrf_form = forms.Form()
        if request.method == 'POST':
            if csrf_form.validate():
                report = CommentModeratorReport.submit(
                    actor=current_auth.user, comment=self.obj
                )
                db.session.commit()
                dispatch_notification(
                    CommentReportReceivedNotification(
                        document=self.obj, fragment=report
                    )
                )
                return {
                    'status': 'ok',
                    'message': _("The comment has been reported as spam"),
                    'comments': self.obj.commentset.views.json_comments(),
                }
            flash(
                _("There was an issue reporting this comment. Please try again"),
                'error',
            )
            return (
                {
                    'status': 'error',
                    'error_code': 'report_spam_error',
                    'error_description': _(
                        "There was an issue reporting this comment. Please try again"
                    ),
                    'error_details': csrf_form.errors,
                },
                400,
            )
        reportspamform_html = render_form(
            form=csrf_form,
            title='Do you want to mark this comment as spam?',
            submit=_("Confirm"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': reportspamform_html}


CommentView.init_app(app)
