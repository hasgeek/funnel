from collections import defaultdict
from datetime import timedelta
from functools import wraps
from io import StringIO
import csv

from sqlalchemy.dialects.postgresql import INTERVAL

from flask import abort, render_template

from coaster.auth import current_auth

from .. import app
from ..models import AuthClient, User, UserSession, auth_client_user_session, db


def requires_dashboard(f):
    """Decorate a view to require dashboard access privilege."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_auth.user or not current_auth.user.is_site_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/dashboard')
@requires_dashboard
def dashboard():
    user_count = User.active_user_count()
    mau = (
        db.session.query(db.func.count(db.func.distinct(UserSession.user_id)))
        .select_from(UserSession)
        .join(User, UserSession.user)
        .filter(
            User.state.ACTIVE,
            UserSession.accessed_at > db.func.utcnow() - timedelta(days=30),
        )
        .scalar()
    )

    return render_template('auth_dashboard.html.jinja2', user_count=user_count, mau=mau)


@app.route('/dashboard/data/users_by_month.csv')
@requires_dashboard
def dashboard_data_users_by_month():
    users_by_month = (
        db.session.query(
            db.func.date_trunc('month', User.created_at).label('month'),
            db.func.count().label('count'),
        )
        .select_from(User)
        .filter(User.state.ACTIVE)
        .group_by('month')
        .order_by('month')
    )

    outfile = StringIO()
    out = csv.writer(outfile, 'excel')
    out.writerow(['month', 'count'])
    for month, count in users_by_month:
        out.writerow([month.strftime('%Y-%m-%d'), count])
    return outfile.getvalue(), 200, {'Content-Type': 'text/plain'}


@app.route('/dashboard/data/users_by_client.csv')
@requires_dashboard
def dashboard_data_users_by_client():
    client_users = defaultdict(
        lambda: {
            'counts': {
                'hour': 0,
                'day': 0,
                'week': 0,
                'month': 0,
                'quarter': 0,
                'halfyear': 0,
                'year': 0,
            }
        }
    )

    for label, interval in (
        ('hour', '1 hour'),
        ('day', '1 day'),
        ('week', '1 week'),
        ('month', '1 month'),
        ('quarter', '3 months'),
        ('halfyear', '6 months'),
        ('year', '1 year'),
    ):
        query_client_users = (
            db.session.query(
                UserSession.user_id.label('user_id'),
                auth_client_user_session.c.auth_client_id.label('auth_client_id'),
            )
            .select_from(UserSession, auth_client_user_session, User)
            .filter(
                UserSession.user_id == User.id,
                auth_client_user_session.c.user_session_id == UserSession.id,
                User.state.ACTIVE,
                auth_client_user_session.c.accessed_at
                >= db.func.utcnow() - db.func.cast(interval, INTERVAL),
            )
            .group_by(auth_client_user_session.c.auth_client_id, UserSession.user_id)
            .subquery()
        )

        clients = (
            db.session.query(
                query_client_users.c.auth_client_id.label('auth_client_id'),
                db.func.count().label('count'),
                AuthClient.title.label('title'),
                AuthClient.website.label('website'),
            )
            .select_from(query_client_users, AuthClient)
            .filter(AuthClient.id == query_client_users.c.auth_client_id)
            .group_by(
                query_client_users.c.auth_client_id,
                AuthClient.title,
                AuthClient.website,
            )
            .order_by(db.text('count DESC'))
            .all()
        )
        for row in clients:
            client_users[row.auth_client_id]['title'] = row.title
            client_users[row.auth_client_id]['website'] = row.website
            client_users[row.auth_client_id]['id'] = row.auth_client_id
            client_users[row.auth_client_id]['counts'][label] = row.count - sum(
                client_users[row.auth_client_id]['counts'].values()
            )

    users_by_client = sorted(
        client_users.values(), key=lambda r: sum(r['counts'].values()), reverse=True
    )

    outfile = StringIO()
    out = csv.writer(outfile, 'excel')
    out.writerow(
        ['title', 'hour', 'day', 'week', 'month', 'quarter', 'halfyear', 'year']
    )

    for row in users_by_client:
        out.writerow(
            [
                row['title'],
                row['counts']['hour'],
                row['counts']['day'],
                row['counts']['week'],
                row['counts']['month'],
                row['counts']['quarter'],
                row['counts']['halfyear'],
                row['counts']['year'],
            ]
        )
    return outfile.getvalue(), 200, {'Content-Type': 'text/plain'}
