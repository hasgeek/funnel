"""Views for notification feed (updates page)."""

from __future__ import annotations

from flask import abort

from baseframe import forms
from coaster.views import ClassView, render_with, requestargs, route

from .. import app
from ..auth import current_auth
from ..models import NotificationRecipient, db
from ..typing import ReturnRenderWith
from .login_session import requires_login


@route('/updates', init_app=app)
class AllNotificationsView(ClassView):
    current_section = 'notifications'  # needed for showing active tab

    @route('', endpoint='notifications', defaults={'unread_only': False})
    @route('unread', endpoint='notifications_unread', defaults={'unread_only': True})
    @requires_login
    @render_with('notification_feed.html.jinja2', json=True)
    @requestargs(('page', int), ('per_page', int))
    def view(
        self, unread_only: bool, page: int = 1, per_page: int = 10
    ) -> ReturnRenderWith:
        pagination = NotificationRecipient.web_notifications_for(
            current_auth.user, unread_only
        ).paginate(page=page, per_page=per_page, max_per_page=100)
        results = {
            'unread_only': unread_only,
            'show_transport_alert': not current_auth.user.has_transport_sms(),
            'notifications': [
                {
                    'notification': nr.current_access(datasets=('primary', 'related')),
                    'html': nr.views.render.web(),
                    'document_type': nr.notification.document_type,
                    'document': (
                        nr.document.current_access(datasets=('primary', 'related'))
                        if nr.document
                        else None
                    ),
                    'fragment_type': nr.notification.fragment_type,
                    'fragment': (
                        nr.fragment.current_access(datasets=('primary', 'related'))
                        if nr.fragment
                        else None
                    ),
                }
                for nr in pagination.items
                if nr.is_not_deleted(revoke=True)
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
        db.session.commit()
        return results

    def unread_count(self) -> int:
        return NotificationRecipient.unread_count_for(current_auth.user)

    @route('count', endpoint='notifications_count')
    def unread(self) -> ReturnRenderWith:
        # This view must NOT have a `@requires_login` decorator as that will insert
        # it as the next page after login
        if current_auth.user:
            return {
                'status': 'ok',
                'unread': self.unread_count(),
            }
        return {'status': 'error', 'error': 'requires_login'}, 400

    @route(
        'mark_read/<eventid_b58>', endpoint='notification_mark_read', methods=['POST']
    )
    @requires_login
    def mark_read(self, eventid_b58: str) -> ReturnRenderWith:
        form = forms.Form()
        del form.form_nonce
        if form.validate_on_submit():
            nr = NotificationRecipient.get_for(current_auth.user, eventid_b58)
            if nr is None:
                abort(404)
            nr.is_read = True
            db.session.commit()
            return {'status': 'ok', 'unread': self.unread_count()}
        return {'status': 'error', 'error': 'csrf'}, 400

    @route(
        'mark_unread/<eventid_b58>',
        endpoint='notification_mark_unread',
        methods=['POST'],
    )
    @requires_login
    def mark_unread(self, eventid_b58: str) -> ReturnRenderWith:
        form = forms.Form()
        del form.form_nonce
        if form.validate_on_submit():
            nr = NotificationRecipient.get_for(current_auth.user, eventid_b58)
            if nr is None:
                abort(404)
            nr.is_read = False
            db.session.commit()
            return {'status': 'ok', 'unread': self.unread_count()}
        return {'status': 'error', 'error': 'csrf'}, 400
