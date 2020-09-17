from flask import abort, redirect

from coaster.auth import current_auth
from coaster.views import ClassView, render_with, requestargs, route
import baseframe.forms as forms

from .. import app, funnelapp, lastuserapp
from ..models import UserNotification, db
from .helpers import app_url_for
from .login_session import requires_login


@route('/updates')
class AllNotificationsView(ClassView):
    current_section = 'notifications'  # needed for showing active tab

    @route('', endpoint='notifications')
    @requires_login
    @render_with('notification_feed.html.jinja2', json=True)
    @requestargs(('page', int), ('per_page', int))
    def view(self, page=1, per_page=10):
        pagination = UserNotification.web_notifications_for(current_auth.user).paginate(
            page=page, per_page=per_page, max_per_page=100
        )
        return {
            'show_transport_alert': not current_auth.user.has_transport_sms(),
            'notifications': [
                {
                    'notification': un.current_access(datasets=('primary', 'related')),
                    'html': un.views.render(),
                    'document_type': un.notification.document_type,
                    'document': un.document.current_access(
                        datasets=('primary', 'related')
                    )
                    if un.document
                    else None,
                    'fragment_type': un.notification.fragment_type,
                    'fragment': un.fragment.current_access(
                        datasets=('primary', 'related')
                    )
                    if un.fragment
                    else None,
                }
                for un in pagination.items
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

    def unread_count(self):
        UserNotification.unread_count_for(current_auth.user)

    @route('count', endpoint='notifications_count')
    @render_with(json=True)
    def unread(self):
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
    @render_with(json=True)
    def mark_read(self, eventid_b58):
        form = forms.Form()
        del form.form_nonce
        if form.validate_on_submit():
            un = UserNotification.get_for(current_auth.user, eventid_b58)
            if not un:
                abort(404)
            un.is_read = True
            db.session.commit()
            return {'status': 'ok', 'unread': self.unread_count()}
        return {'status': 'error', 'error': 'csrf'}, 400

    @route(
        'mark_unread/<eventid_b58>',
        endpoint='notification_mark_unread',
        methods=['POST'],
    )
    @requires_login
    @render_with(json=True)
    def mark_unread(self, eventid_b58):
        form = forms.Form()
        del form.form_nonce
        if forms.validate_on_submit():
            un = UserNotification.get_for(current_auth.user, eventid_b58)
            if not un:
                abort(404)
            un.is_read = False
            db.session.commit()
            return {'status': 'ok', 'unread': self.unread_count()}
        return {'status': 'error', 'error': 'csrf'}, 400


AllNotificationsView.init_app(app)


@route('/updates')
class OtherAppNotificationsView(ClassView):
    @route('', endpoint='notifications')
    def view(self):
        return redirect(app_url_for(app, 'notifications'))

    @route('count', endpoint='notifications_count')
    @render_with(json=True)
    def unread_count(self):
        return {
            'status': 'ok',
            'unread': 0,
        }


OtherAppNotificationsView.init_app(funnelapp)
OtherAppNotificationsView.init_app(lastuserapp)
