from coaster.auth import current_auth
from coaster.views import ClassView, render_with, requestargs, route
import baseframe.forms as forms

from .. import app
from ..models import UserNotification, db
from .login_session import requires_login


@route('/updates')
class AllNotificationsView(ClassView):
    current_section = 'notifications'  # needed for showing active tab

    @route('', endpoint='notifications')
    @requires_login
    @render_with('notification_feed.html.jinja2', json=True)
    @requestargs(('page', int), ('per_page', int))
    def view(self, page=1, per_page=10):
        pagination = UserNotification.query.filter(
            UserNotification.user == current_auth.user
        ).paginate(page=page, per_page=per_page, max_per_page=100)
        return {
            'notifications': [
                {
                    'notification': un.current_access(datasets=('primary', 'related')),
                    'html': un.views.render(),
                    'document_type': un.notification.document_model.__tablename__
                    if un.notification.document_model
                    else None,
                    'document': un.document.current_access(
                        datasets=('primary', 'related')
                    )
                    if un.document
                    else None,
                    'fragment_type': un.notification.fragment_model.__tablename__
                    if un.notification.fragment_model
                    else None,
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

    @route('count', endpoint='notifications_count')
    @requires_login
    @render_with(json=True)
    def unread_count(self):
        return {
            'unread': UserNotification.query.filter(
                UserNotification.user == current_auth.user,
                UserNotification.read_at.is_(None),
            ).count()
        }

    @route('mark_read/<eventid>', endpoint='notification_mark_read', methods=['POST'])
    @requires_login
    @render_with(json=True)
    def mark_read(self, eventid):
        # TODO: Use Base58 ids
        # TODO: Ignore form nonce
        if forms.Form().validate_on_submit():
            # TODO: Use query.get((user_id, eventid)) and do manual 404
            un = UserNotification.query.filter(
                UserNotification.user == current_auth.user,
                UserNotification.eventid == eventid,
            ).one_or_404()
            un.is_read = True
            db.session.commit()
            return {'status': 'ok'}
        return {'status': 'error', 'error': 'csrf'}

    @route(
        'mark_unread/<eventid>', endpoint='notification_mark_unread', methods=['POST']
    )
    @requires_login
    @render_with(json=True)
    def mark_unread(self, eventid):
        # TODO: Use Base58 ids
        # TODO: Ignore form nonce
        if forms.Form().validate_on_submit():
            # TODO: Use query.get((user_id, eventid)) and do manual 404
            un = UserNotification.query.filter(
                UserNotification.user == current_auth.user,
                UserNotification.eventid == eventid,
            ).one_or_404()
            un.is_read = False
            db.session.commit()
            return {'status': 'ok'}
        return {'status': 'error', 'error': 'csrf'}


AllNotificationsView.init_app(app)
