"""Views for site, account and project search."""

from __future__ import annotations

import re
from html import unescape as html_unescape
from typing import Any, TypedDict, TypeVar
from urllib.parse import quote as urlquote

from flask import request, url_for
from markupsafe import Markup
from sqlalchemy.sql import expression

from baseframe import __
from coaster.views import (
    ClassView,
    ModelView,
    UrlForView,
    render_with,
    requestargs,
    requires_roles,
    route,
)

from .. import app, executor
from ..models import (
    Account,
    Comment,
    Commentset,
    Project,
    Proposal,
    ProposalMembership,
    Query,
    SearchModelUnion,
    Session,
    Update,
    db,
    sa,
    visual_field_delimiter,
)
from ..typing import ReturnRenderWith
from ..utils import abort_null
from .helpers import render_redirect
from .mixins import AccountViewMixin, ProjectViewMixin

# --- Definitions ----------------------------------------------------------------------

_Q = TypeVar('_Q', bound=Query)


# PostgreSQL ts_headline markers
pg_startsel = '<mark>'
pg_stopsel = '</mark>'
pg_delimiter = ' … '

# For highlighted text, we need a single line from the page. The highlight must discard
# anything after a line break. Since `hltext` can combine multiple fields using '¦' as
# a field separator, we include that character as a breakpoint. The broken bar character
# was picked due to its historic use as a separator, while having no such modern use.
match_text_breakpoint_re = re.compile('[¦\r\n].*')

# The list of whitespace characters in HTML varies slightly from regex's "\s":
# Regex considers Vertical Tab (\x0B) as whitespace while HTML does not. Since VT is
# an extremely unlikely character in our data, we don't bother to make a more accurate
# regex here.
html_whitespace_re = re.compile(r'\s+', re.ASCII)

# --- Search provider types ------------------------------------------------------------


class SearchProvider:
    """Base class for search providers."""

    #: Label to use in UI
    label: str
    #: Model to query against
    model: type[SearchModelUnion]
    #: Does this model have a title column?
    has_title: bool = True

    @property
    def regconfig(self) -> str:
        """Return PostgreSQL regconfig language, defaulting to English."""
        return self.model.search_vector.type.options.get('regconfig', 'english')

    @property
    def title_column(self) -> sa.ColumnElement[str]:
        """Return a column or column expression representing the object's title."""
        return self.model.title

    @property
    def hltext(self) -> sa.ColumnElement[str]:
        """Return concatenation of all text in search_vector, for highlighting."""
        model_hltext = self.model.search_vector.type.options.get('hltext')
        if model_hltext is not None:
            if callable(model_hltext):
                return model_hltext()
            return model_hltext
        return sa.func.concat_ws(
            visual_field_delimiter,
            *(getattr(self.model, c) for c in self.model.search_vector.type.columns),
        )

    def hltitle_column(
        self, tsquery: sa.sql.functions.Function
    ) -> sa.ColumnElement[str]:
        """Return a column expression for title with search terms highlighted."""
        return sa.func.ts_headline(
            self.regconfig,
            self.title_column,
            tsquery,
            f'HighlightAll=TRUE, StartSel="{pg_startsel}", StopSel="{pg_stopsel}"',
            type_=sa.UnicodeText,
        )

    def hlsnippet_column(
        self, tsquery: sa.sql.functions.Function
    ) -> sa.ColumnElement[str]:
        """Return a column expression for a snippet of text with highlights."""
        return sa.func.ts_headline(
            self.regconfig,
            self.hltext,
            tsquery,
            f'MaxFragments=2, FragmentDelimiter="{pg_delimiter}",'
            f' MinWords=5, MaxWords=20,'
            f' StartSel="{pg_startsel}", StopSel="{pg_stopsel}"',
            type_=sa.UnicodeText,
        )

    def matched_text_column(
        self, tsquery: sa.sql.functions.Function
    ) -> sa.ColumnElement[str]:
        """Return a column expression for matching text, without highlighting."""
        return sa.func.ts_headline(
            self.regconfig,
            self.hltext,
            tsquery,
            'MaxFragments=0, MaxWords=100, StartSel="", StopSel=""',
            type_=sa.UnicodeText,
        )

    # --- Query methods

    def add_order_by(self, tsquery: sa.sql.functions.Function, query: _Q) -> _Q:
        """Add an order_by condition to the query."""
        return query.order_by(
            sa.desc(sa.func.ts_rank_cd(self.model.search_vector, tsquery)),
            self.model.created_at.desc(),
        )

    def all_query(self, tsquery: sa.sql.functions.Function) -> Query:
        """Search entire site."""
        raise NotImplementedError("Subclasses must implement all_query")

    def all_count(self, tsquery: sa.sql.functions.Function) -> int:
        """Return count of results for :meth:`all_query`."""
        return self.all_query(tsquery).options(sa.orm.load_only(self.model.id)).count()


class SearchInAccountProvider(SearchProvider):
    """Base class for search providers that support searching in an account."""

    def account_query(
        self, tsquery: sa.sql.functions.Function, account: Account
    ) -> Query:
        """Search in an account."""
        raise NotImplementedError("Subclasses must implement account_query")

    def account_count(
        self, tsquery: sa.sql.functions.Function, account: Account
    ) -> int:
        """Return count of results for :meth:`account_query`."""
        return (
            self.account_query(tsquery, account)
            .options(sa.orm.load_only(self.model.id))
            .count()
        )


class SearchInProjectProvider(SearchInAccountProvider):
    """Base class for search providers that support searching in a project."""

    def project_query(
        self, tsquery: sa.sql.functions.Function, project: Project
    ) -> Query:
        """Search in a project."""
        raise NotImplementedError("Subclasses must implement project_query")

    def project_count(
        self, tsquery: sa.sql.functions.Function, project: Project
    ) -> int:
        """Return count of results for :meth:`project_query`."""
        return (
            self.project_query(tsquery, project)
            .options(sa.orm.load_only(self.model.id))
            .count()
        )


# --- Search providers -----------------------------------------------------------------


class ProjectSearch(SearchInAccountProvider):
    """Search for projects."""

    label = __("Projects")
    model = Project

    def all_query(self, tsquery: sa.sql.functions.Function) -> Query[Project]:
        """Search entire site for projects."""
        return (
            Project.query.join(Account, Project.account).filter(
                Account.profile_state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Project.search_vector.bool_op('@@')(tsquery),
            )
            # TODO: Replace `start_at` in distance with a new `nearest_session_at`.
            # The existing `next_session_at` is not suitable as it is future-only.
            .order_by(
                # Order by:
                # 1. Projects with start_at/published_at (ts is None == False)
                # 2. Projects without those (ts is None == True)
                sa.case(
                    (Project.start_at.is_(None), Project.published_at),
                    else_=Project.start_at,
                ).is_(None),
                # Second, order by distance from present
                sa.func.abs(
                    sa.func.extract(
                        'epoch',
                        sa.func.utcnow()
                        - sa.case(
                            (Project.start_at.is_not(None), Project.start_at),
                            (
                                Project.published_at.is_not(None),
                                Project.published_at,
                            ),
                            else_=Project.created_at,
                        ),
                    )
                ),
                # Third, order by relevance of search results
                sa.desc(sa.func.ts_rank_cd(Project.search_vector, tsquery)),
            )
        )

    def all_count(self, tsquery: sa.sql.functions.Function) -> int:
        """Return count of matching projects across the entire site."""
        return (
            db.session.query(sa.func.count('*'))
            .select_from(Project)
            .join(Account, Project.account)
            .filter(
                Account.profile_state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Project.search_vector.bool_op('@@')(tsquery),
            )
            .scalar()
        )

    def account_query(
        self, tsquery: sa.sql.functions.Function, account: Account
    ) -> Query[Project]:
        """Search within an account for projects."""
        return Project.query.filter(
            Project.account == account,
            Project.state.PUBLISHED,
            Project.search_vector.bool_op('@@')(tsquery),
        ).order_by(
            # Order by:
            # 1. Projects with start_at/published_at (ts is None == False)
            # 2. Projects without those (ts is None == True)
            sa.case(
                (Project.start_at.is_(None), Project.published_at),
                else_=Project.start_at,
            ).is_(None),
            # Second, order by distance from present
            # TODO: Replace `start_at` in distance with a new `nearest_session_at`.
            # The existing `next_session_at` is not suitable as it is future-only.
            sa.func.abs(
                sa.func.extract(
                    'epoch',
                    sa.func.utcnow()
                    - sa.case(
                        (Project.start_at.isnot(None), Project.start_at),
                        (
                            Project.published_at.isnot(None),
                            Project.published_at,
                        ),
                        else_=Project.created_at,
                    ),
                )
            ),
            # Third, order by relevance of search results
            sa.desc(sa.func.ts_rank_cd(Project.search_vector, tsquery)),
        )


class AccountSearch(SearchProvider):
    """Search for accounts."""

    label = __("Accounts")
    model = Account

    @property
    def hltext(self) -> sa.ColumnElement[str]:
        """Return text from which matches will be highlighted."""
        return sa.func.concat_ws(
            visual_field_delimiter, Account.title, Account.description_html
        )

    def all_query(self, tsquery: sa.sql.functions.Function) -> Query[Account]:
        """Search for accounts."""
        return self.add_order_by(
            tsquery,
            Account.query.filter(
                Account.profile_state.ACTIVE_AND_PUBLIC,
                Account.search_vector.bool_op('@@')(tsquery),
            ),
        )


class SessionSearch(SearchInProjectProvider):
    """Search for sessions."""

    label = __("Sessions")
    model = Session

    def add_order_by(self, tsquery: sa.sql.functions.Function, query: _Q) -> _Q:
        """Add an order_by condition to the query."""
        return query.order_by(
            sa.desc(sa.func.ts_rank_cd(Session.search_vector, tsquery)),
            sa.case(
                (Session.start_at.is_not(None), Session.start_at),
                else_=Session.created_at,
            ).desc(),
        )

    def all_query(self, tsquery: sa.sql.functions.Function) -> Query[Session]:
        """Search for sessions across the site."""
        return self.add_order_by(
            tsquery,
            Session.query.join(Project, Session.project)
            .join(Account, Project.account)
            .outerjoin(Proposal, Session.proposal)
            .filter(
                Account.profile_state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Session.scheduled,
                Session.search_vector.bool_op('@@')(tsquery),
            ),
        )

    def account_query(
        self, tsquery: sa.sql.functions.Function, account: Account
    ) -> Query[Session]:
        """Search for sessions within an account."""
        return self.add_order_by(
            tsquery,
            Session.query.join(Project, Session.project)
            .outerjoin(Proposal, Session.proposal)
            .filter(
                Project.state.PUBLISHED,
                Project.account == account,
                Session.scheduled,
                Session.search_vector.bool_op('@@')(tsquery),
            ),
        )

    def project_query(
        self, tsquery: sa.sql.functions.Function, project: Project
    ) -> Query[Session]:
        """Search for sessions within a project."""
        return self.add_order_by(
            tsquery,
            Session.query.outerjoin(Proposal).filter(
                Session.project == project,
                Session.scheduled,
                Session.search_vector.bool_op('@@')(tsquery),
            ),
        )


class ProposalSearch(SearchInProjectProvider):
    """Search for proposals."""

    label = __("Submissions")
    model = Proposal

    def add_order_by(self, tsquery: sa.sql.functions.Function, query: _Q) -> _Q:
        """Add an order_by condition to the query."""
        return query.order_by(
            sa.desc(sa.func.ts_rank_cd(Proposal.search_vector, tsquery)),
            Proposal.created_at.desc(),
        )

    def all_query(self, tsquery: sa.sql.functions.Function) -> Query[Proposal]:
        """Search for proposals across the site."""
        return self.add_order_by(
            tsquery,
            Proposal.query.join(Project, Proposal.project)
            .join(Account, Project.account)
            .filter(
                Account.profile_state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Proposal.state.PUBLIC,
                sa.or_(
                    Proposal.search_vector.bool_op('@@')(tsquery),
                    ProposalMembership.query.join(Account, ProposalMembership.member)
                    .filter(
                        ProposalMembership.proposal_id == Proposal.id,
                        ProposalMembership.member_id == Account.id,
                        ProposalMembership.is_uncredited.is_(False),
                        ProposalMembership.is_active,
                        Account.search_vector.bool_op('@@')(tsquery),
                    )
                    .exists()
                    .correlate(Proposal),
                ),
            ),
        )

    def account_query(
        self, tsquery: sa.sql.functions.Function, account: Account
    ) -> Query[Proposal]:
        """Search for proposals within an account."""
        return self.add_order_by(
            tsquery,
            Proposal.query.join(Project, Proposal.project).filter(
                Project.state.PUBLISHED,
                Project.account == account,
                Proposal.state.PUBLIC,
                sa.or_(
                    Proposal.search_vector.bool_op('@@')(tsquery),
                    ProposalMembership.query.join(Account, ProposalMembership.member)
                    .filter(
                        ProposalMembership.proposal_id == Proposal.id,
                        ProposalMembership.member_id == Account.id,
                        ProposalMembership.is_uncredited.is_(False),
                        ProposalMembership.is_active,
                        Account.search_vector.bool_op('@@')(tsquery),
                    )
                    .exists()
                    .correlate(Proposal),
                ),
            ),
        )

    def project_query(
        self, tsquery: sa.sql.functions.Function, project: Project
    ) -> Query[Proposal]:
        """Search for proposals within a project."""
        return self.add_order_by(
            tsquery,
            Proposal.query.filter(
                Proposal.project == project,
                Proposal.state.PUBLIC,
                sa.or_(
                    Proposal.search_vector.bool_op('@@')(tsquery),
                    ProposalMembership.query.join(Account, ProposalMembership.member)
                    .filter(
                        ProposalMembership.proposal_id == Proposal.id,
                        ProposalMembership.member_id == Account.id,
                        ProposalMembership.is_uncredited.is_(False),
                        ProposalMembership.is_active,
                        Account.search_vector.bool_op('@@')(tsquery),
                    )
                    .exists()
                    .correlate(Proposal),
                ),
            ),
        )


class UpdateSearch(SearchInProjectProvider):
    """Search for project updates."""

    label = __("Updates")
    model = Update

    def add_order_by(self, tsquery: sa.sql.functions.Function, query: _Q) -> _Q:
        """Add an order_by condition to the query."""
        return query.order_by(
            sa.desc(sa.func.ts_rank_cd(Update.search_vector, tsquery)),
            sa.case(
                (Update.published_at.is_not(None), Update.published_at),
                else_=Update.created_at,
            ).desc(),
        )

    def all_query(self, tsquery: sa.sql.functions.Function) -> Query[Update]:
        """Search for updates across the site."""
        return self.add_order_by(
            tsquery,
            Update.query.join(Project, Update.project)
            .join(Account, Project.account)
            .filter(
                Account.profile_state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Update.state.PUBLISHED,
                Update.visibility_state.PUBLIC,  # TODO: Add role check for RESTRICTED
                Update.search_vector.bool_op('@@')(tsquery),
            ),
        )

    def account_query(
        self, tsquery: sa.sql.functions.Function, account: Account
    ) -> Query[Update]:
        """Search for updates within an account."""
        return self.add_order_by(
            tsquery,
            Update.query.join(Project, Update.project).filter(
                Project.state.PUBLISHED,
                Project.account == account,
                Update.state.PUBLISHED,
                Update.search_vector.bool_op('@@')(tsquery),
            ),
        )

    def project_query(
        self, tsquery: sa.sql.functions.Function, project: Project
    ) -> Query[Update]:
        """Search for updates within a project."""
        return self.add_order_by(
            tsquery,
            Update.query.filter(
                Update.project == project,
                Update.state.PUBLISHED,
                Update.search_vector.bool_op('@@')(tsquery),
            ),
        )


class CommentSearch(SearchInProjectProvider):
    """Search for comments."""

    label = __("Comments")
    model = Comment
    has_title = False  # Comments don't have titles

    def hltitle_column(self, tsquery: sa.sql.functions.Function):
        """Comments don't have titles, so return a null expression here."""
        return expression.null()

    def all_query(self, tsquery: sa.sql.functions.Function) -> Query[Comment]:
        """Search for comments across the site."""
        return (
            Comment.query.join(Account, Comment.posted_by_id == Account.id)
            .join(Project, Project.commentset_id == Comment.commentset_id)
            .join(Account, Project.account)
            .filter(
                Account.profile_state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Comment.state.PUBLIC,
                sa.or_(
                    Comment.search_vector.bool_op('@@')(tsquery),
                    Account.search_vector.bool_op('@@')(tsquery),
                ),
            )
            .order_by(
                sa.desc(sa.func.ts_rank_cd(Comment.search_vector, tsquery)),
                sa.desc(Comment.created_at),
            )
            .union_all(
                Comment.query.join(Account, Comment.posted_by_id == Account.id)
                .join(Proposal, Proposal.commentset_id == Comment.commentset_id)
                .join(Project, Proposal.project)
                .join(Account, Project.account)
                .filter(
                    # FIXME: "Account" is ambiguous here and needs an alias
                    # (for Project.account)
                    Account.profile_state.ACTIVE_AND_PUBLIC,
                    Project.state.PUBLISHED,
                    Comment.state.PUBLIC,
                    sa.or_(
                        Comment.search_vector.bool_op('@@')(tsquery),
                        Account.search_vector.bool_op('@@')(tsquery),
                    ),
                )
                .order_by(
                    sa.desc(sa.func.ts_rank_cd(Comment.search_vector, tsquery)),
                    sa.desc(Comment.created_at),
                ),
                # Add query on future comment-supporting models here
            )
        )

    def account_query(
        self, tsquery: sa.sql.functions.Function, account: Account
    ) -> Query[Comment]:
        """Search for comments within an account."""
        return (
            Comment.query.join(Account, Comment.posted_by_id == Account.id)
            .join(Project, Project.commentset_id == Comment.commentset_id)
            .filter(
                Project.account == account,
                Project.state.PUBLISHED,
                Comment.state.PUBLIC,
                sa.or_(
                    Comment.search_vector.bool_op('@@')(tsquery),
                    Account.search_vector.bool_op('@@')(tsquery),
                ),
            )
            .order_by(
                sa.desc(sa.func.ts_rank_cd(Comment.search_vector, tsquery)),
                sa.desc(Comment.created_at),
            )
            .union_all(
                Comment.query.join(Account, Comment.posted_by_id == Account.id)
                .join(Proposal, Proposal.commentset_id == Comment.commentset_id)
                .join(Project, Proposal.project)
                .filter(
                    Project.account == account,
                    Project.state.PUBLISHED,
                    Comment.state.PUBLIC,
                    sa.or_(
                        Comment.search_vector.bool_op('@@')(tsquery),
                        Account.search_vector.bool_op('@@')(tsquery),
                    ),
                )
                .order_by(
                    sa.desc(sa.func.ts_rank_cd(Comment.search_vector, tsquery)),
                    sa.desc(Comment.created_at),
                ),
                # Add query on future comment-supporting models here
            )
        )

    def project_query(
        self, tsquery: sa.sql.functions.Function, project: Project
    ) -> Query[Comment]:
        """Search for comments within a project."""
        return (
            Comment.query.join(Account, Comment.posted_by_id == Account.id)
            .join(Commentset, Comment.commentset_id == Commentset.id)
            .filter(
                Commentset.id == project.commentset_id,
                Comment.state.PUBLIC,
                sa.or_(
                    Comment.search_vector.bool_op('@@')(tsquery),
                    Account.search_vector.bool_op('@@')(tsquery),
                ),
            )
            .order_by(
                sa.desc(sa.func.ts_rank_cd(Comment.search_vector, tsquery)),
                sa.desc(Comment.created_at),
            )
            .union_all(
                Comment.query.join(Account, Comment.posted_by_id == Account.id)
                .join(
                    Proposal,
                    sa.and_(
                        Proposal.commentset_id == Comment.commentset_id,
                        Proposal.project_id == project.id,
                    ),
                )
                .filter(
                    Comment.state.PUBLIC,
                    sa.or_(
                        Comment.search_vector.bool_op('@@')(tsquery),
                        Account.search_vector.bool_op('@@')(tsquery),
                    ),
                )
                .order_by(
                    sa.desc(sa.func.ts_rank_cd(Comment.search_vector, tsquery)),
                    sa.desc(Comment.created_at),
                ),
                # Add query on future comment-supporting models here
            )
        )


#: Ordered dictionary of search providers
search_providers: dict[str, SearchProvider] = {
    'project': ProjectSearch(),
    'account': AccountSearch(),
    'session': SessionSearch(),
    'submission': ProposalSearch(),
    'update': UpdateSearch(),
    'comment': CommentSearch(),
}


# --- Utilities ---------------------------------------------------------------


def escape_quotes(text: str) -> Markup:
    """
    Escape quotes in text returned by PostgreSQL's ``ts_headline``.

    PostgreSQL strips HTML tags for us, but we also need to escape quotes to safely
    use the text in HTML tag attributes. Typical use is for ARIA labels.
    """
    return Markup(text.replace('"', '&quot;').replace("'", '&#39;'))


def get_tsquery(text: str | None) -> sa.sql.functions.Function:
    """
    Parse a web search query into a PostgreSQL ``tsquery``.

    This function requires ``websearch_to_tsquery`` from PostgreSQL >= 12.
    """
    return sa.func.websearch_to_tsquery(text or '')


def clean_matched_text(text: str) -> str:
    """Extract a contiguous snippet from matched text for browser highlighting."""
    return urlquote(
        html_unescape(
            html_whitespace_re.sub(' ', match_text_breakpoint_re.sub('', text)).strip()
        )
    )


# --- Search functions --------------------------------------------------------


class SearchCountType(TypedDict, total=False):
    """Typed dictionary for :func:`search_counts`."""

    type: str  # noqa: A003
    label: str
    count: int
    job: Any


# @cache.memoize(timeout=300)
def search_counts(
    tsquery: sa.sql.functions.Function,
    account: Account | None = None,
    project: Project | None = None,
) -> list[SearchCountType]:
    """
    Return counts of search results.

    This function requires an active request as it uses Flask-Executor to perform
    queries in parallel.
    """
    results: list[SearchCountType]
    if project is not None:
        results = [
            {
                'type': stype,
                'label': sp.label,
                'job': executor.submit(sp.project_count, tsquery, project),
            }
            for stype, sp in search_providers.items()
            if isinstance(sp, SearchInProjectProvider)
        ]
    elif account is not None:
        results = [
            {
                'type': stype,
                'label': sp.label,
                'job': executor.submit(sp.account_count, tsquery, account),
            }
            for stype, sp in search_providers.items()
            if isinstance(sp, SearchInAccountProvider)
        ]
    else:
        # Not scoped to `account` or `project`:
        results = [
            {
                'type': stype,
                'label': sp.label,
                'job': executor.submit(sp.all_count, tsquery),
            }
            for stype, sp in search_providers.items()
        ]
    # Collect results from all the background jobs
    for resultset in results:
        resultset['count'] = resultset.pop('job').result()
    # Return collected counts
    return results


# @cache.memoize(timeout=300)
def search_results(
    tsquery: sa.sql.functions.Function,
    stype: str,
    page: int = 1,
    per_page: int = 20,
    account: Account | None = None,
    project: Project | None = None,
):
    """Return search results."""
    # Pick up model data for the given type string
    sp = search_providers[stype]

    if project is not None:
        if not isinstance(sp, SearchInProjectProvider):
            raise TypeError(f"No project search for {sp.label}")
        query = sp.project_query(tsquery, project)
    elif account is not None:
        if not isinstance(sp, SearchInAccountProvider):
            raise TypeError(f"No account search for {sp.label}")
        query = sp.account_query(tsquery, account)
    else:
        query = sp.all_query(tsquery)

    # Add the three additional columns to the query and paginate results
    query = query.add_columns(
        sp.hltitle_column(tsquery),
        sp.hlsnippet_column(tsquery),
        sp.matched_text_column(tsquery),
    )
    pagination = query.paginate(page=page, per_page=per_page, max_per_page=100)

    # Return a page of results
    return {
        'items': [
            {
                'title': item.title if sp.has_title else None,
                'title_html': escape_quotes(title) if title is not None else None,
                'url': item.absolute_url
                + '#:~:text='
                + clean_matched_text(matched_text),
                'snippet_html': escape_quotes(snippet),
                'obj': item.current_access(datasets=('primary', 'related')),
            }
            for item, title, snippet, matched_text in pagination.items
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


# --- Views -------------------------------------------------------------------
class SearchView(ClassView):
    current_section = 'search'

    @route('/search', endpoint='search')
    @render_with('search.html.jinja2', json=True)
    @requestargs(('q', abort_null), ('page', int), ('per_page', int))
    def search(
        self, q: str | None = None, page: int = 1, per_page: int = 20
    ) -> ReturnRenderWith:
        """Perform site-level search."""
        tsquery = get_tsquery(q)
        # Can't use @requestargs for stype as it doesn't support name changes
        stype: str | None = abort_null(request.args.get('type'))
        if not db.session.query(tsquery).scalar():
            return render_redirect(url_for('index'), 302)
        if stype is None or stype not in search_providers:
            return {
                'status': 'ok',
                'query': q,
                'type': None,
                'counts': search_counts(tsquery),
            }
        return {
            'status': 'ok',
            'type': stype,
            'query': q,
            'counts': search_counts(tsquery),
            'results': search_results(tsquery, stype, page=page, per_page=per_page),
        }


SearchView.init_app(app)


@Account.views('search')
@route('/<account>')
class AccountSearchView(AccountViewMixin, UrlForView, ModelView):
    @route('search', endpoint='search_account')
    @render_with('search.html.jinja2', json=True)
    @requires_roles({'reader', 'admin'})
    @requestargs(('q', abort_null), ('page', int), ('per_page', int))
    def search(
        self, q: str | None = None, page: int = 1, per_page: int = 20
    ) -> ReturnRenderWith:
        """Perform search within an account."""
        tsquery = get_tsquery(q)
        # Can't use @requestargs as it doesn't support name changes
        stype: str | None = abort_null(request.args.get('type'))
        if not db.session.query(tsquery).scalar():
            return render_redirect(url_for('index'), 302)
        if (
            stype is None
            or stype not in search_providers
            or not isinstance(search_providers[stype], SearchInAccountProvider)
        ):
            return {
                'status': 'ok',
                'type': None,
                'counts': search_counts(tsquery, account=self.obj),
            }
        return {
            'status': 'ok',
            'account': self.obj.current_access(datasets=('primary', 'related')),
            'type': stype,
            'counts': search_counts(tsquery, account=self.obj),
            'results': search_results(
                tsquery, stype, page=page, per_page=per_page, account=self.obj
            ),
        }


AccountSearchView.init_app(app)


@Project.views('search')
@route('/<account>/<project>/')
class ProjectSearchView(ProjectViewMixin, UrlForView, ModelView):
    @route('search', endpoint='search_project')
    @render_with('search.html.jinja2', json=True)
    @requires_roles({'reader', 'crew', 'participant'})
    @requestargs(('q', abort_null), ('page', int), ('per_page', int))
    def search(
        self, q: str | None = None, page: int = 1, per_page: int = 20
    ) -> ReturnRenderWith:
        """Perform search within a project."""
        tsquery = get_tsquery(q)
        # Can't use @requestargs as it doesn't support name changes
        stype: str | None = abort_null(request.args.get('type'))
        if not db.session.query(tsquery).scalar():
            return render_redirect(url_for('index'), 302)
        if (
            stype is None
            or stype not in search_providers
            or not isinstance(search_providers[stype], SearchInProjectProvider)
        ):
            return {
                'status': 'ok',
                'project': self.obj.current_access(datasets=('primary', 'related')),
                'type': None,
                'counts': search_counts(tsquery, project=self.obj),
            }
        return {
            'status': 'ok',
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'type': stype,
            'counts': search_counts(tsquery, project=self.obj),
            'results': search_results(
                tsquery, stype, page=page, per_page=per_page, project=self.obj
            ),
        }


ProjectSearchView.init_app(app)
