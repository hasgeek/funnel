from __future__ import annotations

from typing import Optional, Union

from flask import flash, jsonify, redirect, request, url_for

from baseframe import _, forms
from baseframe.forms import Form, render_form
from coaster.auth import current_auth
from coaster.views import (
    ClassView,
    ModelView,
    UrlForView,
    render_with,
    requestargs,
    requires_roles,
    route,
)

from .. import app
from ..forms import CommentForm, CommentsetSubscribeForm
from ..models import (
    Comment,
    CommentModeratorReport,
    CommentReplyNotification,
    CommentReportReceivedNotification,
    Commentset,
    CommentsetMembership,
    NewCommentNotification,
    Project,
    Proposal,
    User,
    db,
)
from ..proxies import request_wants
from ..signals import project_role_change, proposal_role_change
from ..typing import ReturnRenderWith, ReturnView
from .decorators import etag_cache_for_user, xhr_only
from .login_session import requires_login, requires_user_not_spammy
from .notification import dispatch_notification


@project_role_change.connect
def update_project_commentset_membership(
    project: Project, actor: User, user: User
) -> None:
    if 'participant' in project.roles_for(user):
        project.commentset.add_subscriber(actor=actor, user=user)
    else:
        project.commentset.remove_subscriber(actor=actor, user=user)


@proposal_role_change.connect
def update_proposal_commentset_membership(
    proposal: Proposal, actor: User, user: User
) -> None:
    if 'submitter' in proposal.roles_for(user):
        proposal.commentset.add_subscriber(actor=actor, user=user)
    else:
        proposal.commentset.remove_subscriber(actor=actor, user=user)


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
        if comment.state.PUBLIC or comment.has_replies
    ]


@Commentset.views('url')
def parent_comments_url(obj):
    url = None  # project or proposal object
    if obj.project is not None:
        url = obj.project.url_for('comments', _external=True)
    elif obj.proposal is not None:
        url = obj.proposal.url_for(_external=True)
    return url


@Commentset.views('last_comment', cached_property=True)
def last_comment(obj: Commentset) -> Optional[Comment]:
    comment = obj.last_comment
    if comment:
        return comment.current_access(datasets=('primary', 'related'))
    return None


@route('/comments')
class AllCommentsView(ClassView):
    """View for index of commentsets."""

    current_section = 'comments'

    @route('', endpoint='comments')
    @requires_login
    @xhr_only(lambda: url_for('index', _anchor='comments'))
    @etag_cache_for_user(
        'comment_sidebar', 1, 60, 60, query_params={'page', 'per_page'}
    )
    @render_with('unread_comments.html.jinja2', json=True)
    @requestargs(('page', int), ('per_page', int))
    def view(self, page: int = 1, per_page: int = 20) -> ReturnRenderWith:
        query = CommentsetMembership.for_user(current_auth.user)
        pagination = query.paginate(page=page, per_page=per_page, max_per_page=100)
        result = {
            'commentset_memberships': [
                {
                    'parent_type': cm.commentset.parent_type,
                    'parent': cm.commentset.parent.current_access(
                        datasets=('primary', 'related')
                    ),
                    'commentset_url': cm.commentset.url_for(),
                    'last_seen_at': cm.last_seen_at,
                    'new_comment_count': cm.new_comment_count,
                    'last_comment_at': cm.commentset.last_comment_at,
                    'last_comment': cm.commentset.views.last_comment,
                }
                for cm in pagination.items
            ],
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages,
            'next_num': pagination.next_num,
            'prev_num': pagination.prev_num,
            'count': pagination.total,
        }
        return result


AllCommentsView.init_app(app)


@route('/comments/<commentset>')
class CommentsetView(UrlForView, ModelView):
    """Views for commentset display within a host document."""

    model = Commentset
    route_model_map = {'commentset': 'uuid_b58'}
    obj: Commentset

    def loader(self, commentset) -> Commentset:
        return Commentset.query.filter(Commentset.uuid_b58 == commentset).one_or_404()

    @route('', methods=['GET'])
    def view(self):
        subscribed = bool(self.obj.current_roles.document_subscriber)
        if request_wants.json:
            return jsonify(
                {'subscribed': subscribed, 'comments': self.obj.views.json_comments()}
            )
        return redirect(self.obj.views.url(), code=303)

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_user_not_spammy(lambda self: self.obj.url_for())
    @render_with(json=True)
    def new(self):
        commentform = CommentForm()
        if commentform.validate_on_submit():
            if not self.obj.post_comment.is_available:
                return {
                    'status': 'error',
                    'error': 'disabled',
                    'error_description': _("Commenting is disabled"),
                }, 422

            comment = self.obj.post_comment(
                current_auth.actor, commentform.message.data
            )

            if self.obj.current_roles.document_subscriber:
                self.obj.update_last_seen_at(user=current_auth.actor)
            else:
                self.obj.add_subscriber(
                    actor=current_auth.actor, user=current_auth.actor
                )
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
        subscribe_form = CommentsetSubscribeForm()
        subscribe_form.form_nonce.data = subscribe_form.form_nonce.default()
        if subscribe_form.validate_on_submit():
            if subscribe_form.subscribe.data:
                self.obj.add_subscriber(actor=current_auth.user, user=current_auth.user)
                db.session.commit()
                return {
                    'status': 'ok',
                    'message': _("You will be notified of new comments"),
                    'form_nonce': subscribe_form.form_nonce.data,
                }
            self.obj.remove_subscriber(actor=current_auth.user, user=current_auth.user)
            db.session.commit()
            return {
                'status': 'ok',
                'message': _("You will no longer be notified for new comments"),
                'form_nonce': subscribe_form.form_nonce.data,
            }
        return {
            'status': 'error',
            # FIXME: In other views this is `error_details`
            'details': subscribe_form.errors,
            # FIXME: this needs `error` (code) and `error_description` (text) keys
            'message': _("Request expired. Reload and try again"),
            'form_nonce': subscribe_form.form_nonce.data,
        }, 400

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
            'error': 'update_seen_at_error',
            'error_description': _("This page timed out. Reload and try again"),
            'error_details': csrf_form.errors,
        }, 422


CommentsetView.init_app(app)


@route('/comments/<commentset>/<comment>')
class CommentView(UrlForView, ModelView):
    """Views for a single comment."""

    model = Comment
    route_model_map = {'commentset': 'commentset.uuid_b58', 'comment': 'uuid_b58'}
    obj: Comment

    def loader(self, commentset, comment) -> Union[Comment, Commentset]:
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

    def after_loader(self) -> Optional[ReturnView]:
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
    @requires_user_not_spammy(lambda self: self.obj.url_for())
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
                report, created = CommentModeratorReport.submit(
                    actor=current_auth.user, comment=self.obj
                )
                if created:
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
                _("There was an issue reporting this comment. Try again?"),
                'error',
            )
            return (
                {
                    'status': 'error',
                    'error': 'report_spam_error',
                    'error_description': _(
                        "There was an issue reporting this comment. Try again?"
                    ),
                    'error_details': csrf_form.errors,
                },
                400,
            )
        reportspamform_html = render_form(
            form=csrf_form,
            title=_("Do you want to mark this comment as spam?"),
            submit=_("Confirm"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': reportspamform_html}


CommentView.init_app(app)
