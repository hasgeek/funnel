"""Siteadmin views."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta
from functools import wraps
from io import StringIO
from typing import Any, Callable, Dict, Optional

from flask import abort, current_app, flash, render_template, request, url_for
from sqlalchemy.dialects.postgresql import INTERVAL

try:
    import rq_dashboard
except ModuleNotFoundError:
    rq_dashboard = None

from baseframe import _
from baseframe.forms import Form
from coaster.auth import current_auth
from coaster.views import ClassView, render_with, requestargs, route

from .. import app
from ..forms import ModeratorReportForm
from ..models import (
    MODERATOR_REPORT_TYPE,
    AuthClient,
    Comment,
    CommentModeratorReport,
    User,
    UserSession,
    auth_client_user_session,
    db,
    sa,
)
from ..typing import P, ReturnRenderWith, ReturnResponse, ReturnView, T
from ..utils import abort_null
from .helpers import render_redirect
from .login_session import requires_login

# XXX: Replace with TypedDict when upgrading to Python 3.8+
counts_template = {
    'hour': 0,
    'day': 0,
    'week': 0,
    'month': 0,
    'quarter': 0,
    'halfyear': 0,
    'year': 0,
}


@dataclass
class AuthClientUserReport:
    """Data model for auth client user activity report."""

    auth_client_id: int
    title: str
    website: str
    counts: Dict[str, int] = field(default_factory=counts_template.copy)


@dataclass
class ReportCounter:
    """Data structure for counting report types against frequency of reports."""

    report_type: int
    frequency: int


def requires_siteadmin(f: Callable[P, T]) -> Callable[P, T]:
    """Decorate a view to require siteadmin privilege."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if not current_auth.user or not current_auth.user.is_site_admin:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


def requires_site_editor(f: Callable[P, T]) -> Callable[P, T]:
    """Decorate a view to require site editor privilege."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if not current_auth.user or not current_auth.user.is_site_editor:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


def requires_user_moderator(f: Callable[P, T]) -> Callable[P, T]:
    """Decorate a view to require user moderator privilege."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if not current_auth.user or not current_auth.user.is_user_moderator:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


def requires_comment_moderator(f: Callable[P, T]) -> Callable[P, T]:
    """Decorate a view to require comment moderator privilege."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        if not current_auth.user or not current_auth.user.is_comment_moderator:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


def requires_sysadmin(f: Callable[P, T]) -> Callable[P, T]:
    """Decorate a view to require sysadmin privilege."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        if not current_auth.user or not current_auth.user.is_sysadmin:
            abort(403)
        return f(*args, **kwargs)

    return wrapper


@route('/siteadmin')
class SiteadminView(ClassView):
    """Site administrator views."""

    __decorators__ = [requires_login]
    current_section = 'siteadmin'  # needed for showing active tab

    @route('', endpoint='siteadmin')
    @requires_siteadmin
    def dashboard(self) -> ReturnView:
        """Render siteadmin dashboard landing page."""
        user_count = User.active_user_count()
        mau = (
            db.session.query(sa.func.count(sa.func.distinct(UserSession.user_id)))
            .select_from(UserSession)
            .join(User, UserSession.user)
            .filter(
                User.state.ACTIVE,
                UserSession.accessed_at > sa.func.utcnow() - timedelta(days=30),
            )
            .scalar()
        )

        return render_template(
            'auth_dashboard.html.jinja2', user_count=user_count, mau=mau
        )

    @route('data/users_by_month.csv', endpoint='dashboard_data_users_by_month')
    @requires_siteadmin
    def dashboard_data_users_by_month(self) -> ReturnView:
        """Render CSV of registered users by month."""
        users_by_month = (
            db.session.query(
                sa.func.date_trunc('month', User.created_at).label('month'),
                sa.func.count().label('count'),
            )
            .select_from(User)
            .filter(User.state.ACTIVE)
            .group_by('month')
            .order_by('month')
        )

        outfile = StringIO(newline='')
        out = csv.writer(outfile, 'excel')
        out.writerow(['month', 'count'])
        for month, count in users_by_month:
            out.writerow([month.strftime('%Y-%m-%d'), count])
        return outfile.getvalue(), 200, {'Content-Type': 'text/plain'}

    @route('data/users_by_client.csv', endpoint='dashboard_data_users_by_client')
    @requires_siteadmin
    def dashboard_data_users_by_client(self) -> ReturnView:
        """Render CSV of active user counts per time period and auth client."""
        client_users: Dict[int, AuthClientUserReport] = {}

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
                    >= sa.func.utcnow() - sa.func.cast(interval, INTERVAL),
                )
                .group_by(
                    auth_client_user_session.c.auth_client_id, UserSession.user_id
                )
                .subquery()
            )

            clients = (
                db.session.query(
                    query_client_users.c.auth_client_id.label('auth_client_id'),
                    sa.func.count().label('count'),
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
                .order_by(sa.text('count DESC'))
                .all()
            )
            for row in clients:
                if row.auth_client_id not in client_users:
                    client_users[row.auth_client_id] = AuthClientUserReport(
                        auth_client_id=row.auth_client_id,
                        title=row.title,
                        website=row.website,
                    )
                client_users[row.auth_client_id].counts[label] = row.count - sum(
                    client_users[row.auth_client_id].counts.values()
                )

        users_by_client = sorted(
            client_users.values(),
            key=lambda r: sum(r.counts.values()),
            reverse=True,
        )

        outfile = StringIO(newline='')
        out = csv.writer(outfile, 'excel')
        out.writerow(
            ['title', 'hour', 'day', 'week', 'month', 'quarter', 'halfyear', 'year']
        )

        for row in users_by_client:
            out.writerow(
                [
                    row.title,
                    row.counts['hour'],
                    row.counts['day'],
                    row.counts['week'],
                    row.counts['month'],
                    row.counts['quarter'],
                    row.counts['halfyear'],
                    row.counts['year'],
                ]
            )
        return outfile.getvalue(), 200, {'Content-Type': 'text/plain'}

    @route('comments', endpoint='siteadmin_comments', methods=['GET', 'POST'])
    @requires_comment_moderator
    @render_with('siteadmin_comments.html.jinja2')
    @requestargs(('query', abort_null), ('page', int), ('per_page', int))
    def comments(
        self, query: str = '', page: Optional[int] = None, per_page: int = 100
    ) -> ReturnRenderWith:
        """Render a list of all comments matching a query."""
        comments = Comment.query.filter(Comment.state.REPORTABLE).order_by(
            Comment.created_at.desc()
        )
        tsquery = sa.func.websearch_to_tsquery(query or '')
        if query:
            comments = comments.join(User).filter(
                sa.or_(
                    Comment.search_vector.bool_op('@@')(tsquery),
                    User.search_vector.bool_op('@@')(tsquery),
                )
            )

        pagination = comments.paginate(page=page, per_page=per_page)

        return {
            'title': _("Comments"),
            'query': query,
            'comments': pagination.items,
            'total_comments': pagination.total,
            'pages': list(range(1, pagination.pages + 1)),  # list of page numbers
            'current_page': pagination.page,
            'comment_spam_form': Form(),
        }

    @route(
        'comments/markspam',
        endpoint='siteadmin_comments_spam',
        methods=['POST'],
    )
    @requires_comment_moderator
    def markspam(self) -> ReturnResponse:
        """Mark comments as spam."""
        comment_spam_form = Form()
        comment_spam_form.form_nonce.data = comment_spam_form.form_nonce.default()
        # TODO: Create a CommentReportForm that has a QuerySelectMultiField on Comment.
        # Avoid request.form.getlist('comment_id') here
        if comment_spam_form.validate_on_submit():
            comments = Comment.query.filter(
                Comment.uuid_b58.in_(request.form.getlist('comment_id'))
            )
            for comment in comments:
                CommentModeratorReport.submit(actor=current_auth.user, comment=comment)
            db.session.commit()
            flash(_("Comment(s) successfully reported as spam"), category='info')
        else:
            flash(
                _("There was a problem marking the comments as spam. Try again?"),
                category='error',
            )

        return render_redirect(url_for('siteadmin_comments'))

    @route('comments/review', endpoint='siteadmin_review_comments_random')
    @requires_comment_moderator
    def review_random_comment(self) -> ReturnResponse:
        """Evaluate an existing comment spam report, selected at random."""
        random_report = CommentModeratorReport.get_one(exclude_user=current_auth.user)
        if random_report is not None:
            return render_redirect(
                url_for('siteadmin_review_comment', report=random_report.uuid_b58)
            )
        flash(_("There are no comment reports to review at this time"), 'error')
        return render_redirect(url_for('siteadmin_comments'))

    @route(
        'comments/review/<report>',
        endpoint='siteadmin_review_comment',
        methods=['GET', 'POST'],
    )
    @requires_comment_moderator
    @render_with('siteadmin_review_comment.html.jinja2')
    def review_comment(self, report: str) -> ReturnRenderWith:
        """Evaluate an existing comment spam report."""
        comment_report: CommentModeratorReport = CommentModeratorReport.query.filter_by(
            uuid_b58=report
        ).one_or_404()

        if comment_report.comment.is_reviewed_by(current_auth.user):
            flash(_("You cannot review same comment twice"), 'error')
            return render_redirect(url_for('siteadmin_review_comments_random'))

        if comment_report.user == current_auth.user:
            flash(_("You cannot review your own report"), 'error')
            return render_redirect(url_for('siteadmin_review_comments_random'))

        # get all existing reports for the same comment
        existing_reports = CommentModeratorReport.get_all(
            exclude_user=current_auth.user
        ).filter_by(comment_id=comment_report.comment_id)

        if comment_report.comment.state.SPAM:
            # if a comment is marked as spam by some other mechanism, like direct
            # DB update, all the reports will be left hanging. We can mark then as
            # resolved. Not sure if there is a better alternative for `resolved_at`.
            flash(_("This comment has already been marked as spam"), 'error')
            CommentModeratorReport.query.filter_by(
                comment=comment_report.comment
            ).update({'resolved_at': sa.func.utcnow()}, synchronize_session='fetch')
            db.session.commit()
            # Redirect to a new report
            return render_redirect(url_for('siteadmin_review_comments_random'))

        report_form = ModeratorReportForm()
        report_form.form_nonce.data = report_form.form_nonce.default()

        if report_form.validate_on_submit():
            # get other reports for same comment
            # existing report count will be greater than 0 because
            # current report exists and it's not by the current user.
            report_counter = Counter(
                [exreport.report_type for exreport in existing_reports]
                + [report_form.report_type.data]
            )
            # if there is already a report for this comment
            most_common_two = [
                ReportCounter(report_type, frequency)
                for report_type, frequency in report_counter.most_common(2)
            ]
            # Possible values of most_common_two -
            # - [(1, 2)] - if both existing and current reports are same or
            # - [(1, 2), (0, 1), (report_type, frequency)] - conflicting reports
            if (
                len(most_common_two) == 1
                or most_common_two[0].frequency > most_common_two[1].frequency
            ):
                if most_common_two[0].report_type == MODERATOR_REPORT_TYPE.SPAM:
                    comment_report.comment.mark_spam()
                elif most_common_two[0].report_type == MODERATOR_REPORT_TYPE.OK:
                    if not comment_report.comment.state.DELETED:
                        comment_report.comment.mark_not_spam()
                with db.session.no_autoflush:
                    CommentModeratorReport.query.filter_by(
                        comment=comment_report.comment
                    ).update(
                        {'resolved_at': sa.func.utcnow()}, synchronize_session='fetch'
                    )
            else:
                # current report is different from existing report and
                # no report has majority frequency.
                # e.g. existing report was spam, current report is not spam,
                # we'll create the new report and wait for a 3rd report.
                new_report = CommentModeratorReport(
                    user=current_auth.user,
                    comment=comment_report.comment,
                    report_type=report_form.report_type.data,
                )
                db.session.add(new_report)
            db.session.commit()

            # Redirect to a new report
            return render_redirect(url_for('siteadmin_review_comments_random'))

        current_app.logger.debug(report_form.errors)

        return {
            'report': comment_report,
            'report_form': report_form,
        }


SiteadminView.init_app(app)


def init_rq_dashboard():
    """Register RQ Dashboard Blueprint if available for import."""
    if rq_dashboard is not None:
        rq_dashboard.blueprint.before_request(
            lambda: None
            if current_auth and current_auth.user.is_sysadmin
            else abort(403)
        )
        app.register_blueprint(rq_dashboard.blueprint, url_prefix='/siteadmin/rq')
