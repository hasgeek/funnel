from __future__ import annotations

from html import unescape as html_unescape
from typing import Any, List, Optional
from urllib.parse import quote as urlquote
import re

from sqlalchemy.sql.elements import ColumnElement
import sqlalchemy.sql.expression as expression

from flask import Markup, redirect, request, url_for

from typing_extensions import TypedDict

from baseframe import __
from coaster.sqlalchemy import Query
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
    Comment,
    Commentset,
    Organization,
    Profile,
    Project,
    Proposal,
    ProposalMembership,
    Session,
    Update,
    User,
    db,
    visual_field_delimiter,
)
from ..utils import abort_null
from .mixins import ProfileViewMixin, ProjectViewMixin

# --- Definitions ----------------------------------------------------------------------

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
    model: db.Model
    #: Does this model have a title column?
    has_title: bool = True

    @property
    def regconfig(self) -> str:
        """Return PostgreSQL regconfig language, defaulting to English."""
        return self.model.search_vector.type.options.get('regconfig', 'english')

    @property
    def title_column(self):
        """Return a column or column expression representing the object's title."""
        return self.model.title

    @property
    def hltext(self) -> ColumnElement:
        """Return concatenation of all text in search_vector, for highlighting."""
        model_hltext = self.model.search_vector.type.options.get('hltext')
        if model_hltext is not None:
            if callable(model_hltext):
                return model_hltext()
            return model_hltext
        return db.func.concat_ws(
            visual_field_delimiter,
            *(getattr(self.model, c) for c in self.model.search_vector.type.columns),
        )

    def hltitle_column(self, squery: str) -> ColumnElement:
        """Return a column expression for title with search terms highlighted."""
        return db.func.ts_headline(
            self.regconfig,
            self.title_column,
            db.func.to_tsquery(squery),
            'HighlightAll=TRUE, StartSel="%s", StopSel="%s"'
            % (pg_startsel, pg_stopsel),
            type_=db.UnicodeText,
        )

    def hlsnippet_column(self, squery: str) -> ColumnElement:
        """Return a column expression for a snippet of text with highlights."""
        return db.func.ts_headline(
            self.regconfig,
            self.hltext,
            db.func.to_tsquery(squery),
            'MaxFragments=2, FragmentDelimiter="%s",'
            ' MinWords=5, MaxWords=20,'
            ' StartSel="%s", StopSel="%s"' % (pg_delimiter, pg_startsel, pg_stopsel),
            type_=db.UnicodeText,
        )

    def matched_text_column(self, squery: str) -> ColumnElement:
        """Return a column expression for matching text, without highlighting."""
        return db.func.ts_headline(
            self.regconfig,
            self.hltext,
            db.func.to_tsquery(squery),
            'MaxFragments=0, MaxWords=100, StartSel="", StopSel=""',
            type_=db.UnicodeText,
        )

    # --- Query methods

    def add_order_by(self, squery: str, query: Query) -> Query:
        """Add an order_by condition to the query."""
        return query.order_by(
            db.desc(db.func.ts_rank_cd(self.model.search_vector, squery)),
            self.model.created_at.desc(),
        )

    def all_query(self, squery: str) -> Query:
        """Search entire site."""
        ...

    def all_count(self, squery: str) -> int:
        """Return count of results for :meth:`all_query`."""
        return self.all_query(squery).options(db.load_only(self.model.id)).count()


class SearchInProfileProvider(SearchProvider):
    """Base class for search providers that support searching in a profile."""

    def profile_query(self, squery: str, profile: Profile) -> Query:
        """Search in a profile."""
        ...

    def profile_count(self, squery: str, profile: Profile) -> int:
        """Return count of results for :meth:`profile_query`."""
        return (
            self.profile_query(squery, profile)
            .options(db.load_only(self.model.id))
            .count()
        )


class SearchInProjectProvider(SearchInProfileProvider):
    """Base class for search providers that support searching in a profile."""

    def project_query(self, squery: str, project: Project) -> Query:
        """Search in a project."""
        ...

    def project_count(self, squery: str, project: Project) -> int:
        """Return count of results for :meth:`project_query`."""
        return (
            self.project_query(squery, project)
            .options(db.load_only(self.model.id))
            .count()
        )


# --- Search providers -----------------------------------------------------------------


class ProjectSearch(SearchInProfileProvider):
    """Search for projects."""

    label = __("Projects")
    model = Project

    def all_query(self, squery: str) -> Query:
        """Search entire site for projects."""
        return (
            Project.query.join(Profile, Project.profile_id == Profile.id)
            .outerjoin(User, Profile.user_id == User.id)
            .outerjoin(Organization, Profile.organization_id == Organization.id)
            .filter(
                Profile.state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                db.or_(
                    # Search conditions. Any of:
                    # 1. Project has search terms
                    Project.search_vector.match(squery),
                    # 2. Project's profile (for org) has a match in the org title
                    Organization.search_vector.match(squery),
                    # 3. Project's profile (for user) has a match in the user's name
                    User.search_vector.match(squery),
                ),
            )
            .options(db.joinedload(Project.profile))
            # TODO: Replace `start_at` in distance with a new `nearest_session_at`.
            # The existing `next_session_at` is not suitable as it is future-only.
            .order_by(
                # Order by:
                # 1. Projects with start_at/published_at (ts is None == False)
                # 2. Projects without those (ts is None == True)
                db.case(
                    [(Project.start_at.is_(None), Project.published_at)],
                    else_=Project.start_at,
                ).is_(None),
                # Second, order by distance from present
                db.func.abs(
                    db.func.extract(
                        'epoch',
                        db.func.utcnow()
                        - db.case(
                            [
                                (Project.start_at.isnot(None), Project.start_at),
                                (
                                    Project.published_at.isnot(None),
                                    Project.published_at,
                                ),
                            ],
                            else_=Project.created_at,
                        ),
                    )
                ),
                # Third, order by relevance of search results
                db.desc(db.func.ts_rank_cd(Project.search_vector, squery)),
            )
        )

    def all_count(self, squery: str) -> int:
        """Return count of matching projects across the entire site."""
        return (
            db.session.query(db.func.count('*'))
            .select_from(Project)
            .join(Profile, Project.profile_id == Profile.id)
            .outerjoin(User, Profile.user_id == User.id)
            .outerjoin(Organization, Profile.organization_id == Organization.id)
            .filter(
                Profile.state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                db.or_(
                    Project.search_vector.match(squery),
                    Organization.search_vector.match(squery),
                    User.search_vector.match(squery),
                ),
            )
            .scalar()
        )

    def profile_query(self, squery: str, profile: Profile) -> Query:
        """Search within a profile for projects."""
        return (
            Project.query.filter(
                Project.profile == profile,
                Project.state.PUBLISHED,
                Project.search_vector.match(squery),
            )
            # .options(db.joinedload(Profile))  # Disabled because it breaks add_columns
            .order_by(
                # Order by:
                # 1. Projects with start_at/published_at (ts is None == False)
                # 2. Projects without those (ts is None == True)
                db.case(
                    [(Project.start_at.is_(None), Project.published_at)],
                    else_=Project.start_at,
                ).is_(None),
                # Second, order by distance from present
                # TODO: Replace `start_at` in distance with a new `nearest_session_at`.
                # The existing `next_session_at` is not suitable as it is future-only.
                db.func.abs(
                    db.func.extract(
                        'epoch',
                        db.func.utcnow()
                        - db.case(
                            [
                                (Project.start_at.isnot(None), Project.start_at),
                                (
                                    Project.published_at.isnot(None),
                                    Project.published_at,
                                ),
                            ],
                            else_=Project.created_at,
                        ),
                    )
                ),
                # Third, order by relevance of search results
                db.desc(db.func.ts_rank_cd(Project.search_vector, squery)),
            )
        )


class ProfileSearch(SearchProvider):
    """Search for profiles."""

    label = __("Profiles")
    model = Profile

    @property
    def title_column(self) -> ColumnElement:
        """Return title from user or organization that the profile is attached to."""
        return db.case(
            [
                (Profile.user_id.isnot(None), User.fullname),
                (Profile.organization_id.isnot(None), Organization.title),
            ],
            else_=Profile.name,
        )

    @property
    def hltext(self) -> ColumnElement:
        """Return text from which matches will be highlighted."""
        return db.func.concat_ws(
            visual_field_delimiter, self.title_column, Profile.description_html
        )

    def all_query(self, squery: str) -> Query:
        """Search for profiles."""
        return self.add_order_by(
            squery,
            Profile.query.outerjoin(User)
            .outerjoin(Organization)
            .filter(
                Profile.state.ACTIVE_AND_PUBLIC,
                db.or_(
                    Profile.search_vector.match(squery),
                    User.search_vector.match(squery),
                    Organization.search_vector.match(squery),
                ),
            ),
        )


class SessionSearch(SearchInProjectProvider):
    """Search for sessions."""

    label = __("Sessions")
    model = Session

    def add_order_by(self, squery: str, query: Query) -> Query:
        """Add an order_by condition to the query."""
        return query.order_by(
            db.desc(db.func.ts_rank_cd(Session.search_vector, squery)),
            db.case(
                [(Session.start_at.isnot(None), Session.start_at)],
                else_=Session.created_at,
            ).desc(),
        )

    def all_query(self, squery: str) -> Query:
        """Search for sessions across the site."""
        return self.add_order_by(
            squery,
            Session.query.join(Project, Session.project)
            .join(Profile, Project.profile)
            .outerjoin(Proposal, Session.proposal)
            .filter(
                Profile.state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Session.scheduled,
                Session.search_vector.match(squery),
            ),
        )

    def profile_query(self, squery: str, profile: Profile) -> Query:
        """Search for sessions within a profile."""
        return self.add_order_by(
            squery,
            Session.query.join(Project, Session.project)
            .outerjoin(Proposal, Session.proposal)
            .filter(
                Project.state.PUBLISHED,
                Project.profile == profile,
                Session.scheduled,
                Session.search_vector.match(squery),
            ),
        )

    def project_query(self, squery: str, project: Project) -> Query:
        """Search for sessions within a project."""
        return self.add_order_by(
            squery,
            Session.query.outerjoin(Proposal).filter(
                Session.project == project,
                Session.scheduled,
                Session.search_vector.match(squery),
            ),
        )


class ProposalSearch(SearchInProjectProvider):
    """Search for proposals."""

    label = __("Submissions")
    model = Proposal

    def add_order_by(self, squery: str, query: Query) -> Query:
        """Add an order_by condition to the query."""
        return query.order_by(
            db.desc(db.func.ts_rank_cd(Proposal.search_vector, squery)),
            Proposal.created_at.desc(),
        )

    def all_query(self, squery: str) -> Query:
        """Search for proposals across the site."""
        return self.add_order_by(
            squery,
            Proposal.query.join(Project, Proposal.project)
            .join(Profile, Project.profile)
            .filter(
                Profile.state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Proposal.state.PUBLIC,
                db.or_(
                    Proposal.search_vector.match(squery),
                    ProposalMembership.query.join(User, ProposalMembership.user)
                    .filter(
                        ProposalMembership.proposal_id == Proposal.id,
                        ProposalMembership.user_id == User.id,
                        ProposalMembership.is_uncredited.is_(False),
                        ProposalMembership.is_active,
                        User.search_vector.match(squery),
                    )
                    .exists()
                    .correlate(Proposal),
                ),
            ),
        )

    def profile_query(self, squery: str, profile: Profile) -> Query:
        """Search for proposals within a profile."""
        return self.add_order_by(
            squery,
            Proposal.query.join(Project, Proposal.project).filter(
                Project.state.PUBLISHED,
                Project.profile == profile,
                Proposal.state.PUBLIC,
                db.or_(
                    Proposal.search_vector.match(squery),
                    ProposalMembership.query.join(User, ProposalMembership.user)
                    .filter(
                        ProposalMembership.proposal_id == Proposal.id,
                        ProposalMembership.user_id == User.id,
                        ProposalMembership.is_uncredited.is_(False),
                        ProposalMembership.is_active,
                        User.search_vector.match(squery),
                    )
                    .exists()
                    .correlate(Proposal),
                ),
            ),
        )

    def project_query(self, squery: str, project: Project) -> Query:
        """Search for proposals within a project."""
        return self.add_order_by(
            squery,
            Proposal.query.filter(
                Proposal.project == project,
                Proposal.state.PUBLIC,
                db.or_(
                    Proposal.search_vector.match(squery),
                    ProposalMembership.query.join(User, ProposalMembership.user)
                    .filter(
                        ProposalMembership.proposal_id == Proposal.id,
                        ProposalMembership.user_id == User.id,
                        ProposalMembership.is_uncredited.is_(False),
                        ProposalMembership.is_active,
                        User.search_vector.match(squery),
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

    def add_order_by(self, squery: str, query: Query) -> Query:
        """Add an order_by condition to the query."""
        return query.order_by(
            db.desc(db.func.ts_rank_cd(Update.search_vector, squery)),
            db.case(
                [(Update.published_at.isnot(None), Update.published_at)],
                else_=Update.created_at,
            ).desc(),
        )

    def all_query(self, squery: str) -> Query:
        """Search for updates across the site."""
        return self.add_order_by(
            squery,
            Update.query.join(Project, Update.project)
            .join(Profile, Project.profile)
            .filter(
                Profile.state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Update.state.PUBLISHED,
                Update.visibility_state.PUBLIC,  # TODO: Add role check for RESTRICTED
                Update.search_vector.match(squery),
            ),
        )

    def profile_query(self, squery: str, profile: Profile) -> Query:
        """Search for updates within a profile."""
        return self.add_order_by(
            squery,
            Update.query.join(Project, Update.project).filter(
                Project.state.PUBLISHED,
                Project.profile == profile,
                Update.state.PUBLISHED,
                Update.search_vector.match(squery),
            ),
        )

    def project_query(self, squery: str, project: Project) -> Query:
        """Search for updates within a project."""
        return self.add_order_by(
            squery,
            Update.query.filter(
                Update.project == project,
                Update.state.PUBLISHED,
                Update.search_vector.match(squery),
            ),
        )


class CommentSearch(SearchInProjectProvider):
    """Search for comments."""

    label = __("Comments")
    model = Comment
    has_title = False  # Comments don't have titles

    def hltitle_column(self, squery: str):
        """Comments don't have titles, so return a null expression here."""
        return expression.null()

    def all_query(self, squery: str) -> Query:
        """Search for comments across the site."""
        return (
            Comment.query.join(User, Comment.user_id == User.id)
            .join(Project, Project.commentset_id == Comment.commentset_id)
            .join(Profile, Project.profile_id == Profile.id)
            .filter(
                Profile.state.ACTIVE_AND_PUBLIC,
                Project.state.PUBLISHED,
                Comment.state.PUBLIC,
                db.or_(
                    Comment.search_vector.match(squery),
                    User.search_vector.match(squery),
                ),
            )
            .order_by(
                db.desc(db.func.ts_rank_cd(Comment.search_vector, squery)),
                db.desc(Comment.created_at),
            )
            .union_all(
                Comment.query.join(User, Comment.user_id == User.id)
                .join(Proposal, Proposal.commentset_id == Comment.commentset_id)
                .join(Project, Proposal.project_id == Project.id)
                .join(Profile, Project.profile_id == Profile.id)
                .filter(
                    Profile.state.ACTIVE_AND_PUBLIC,
                    Project.state.PUBLISHED,
                    Comment.state.PUBLIC,
                    db.or_(
                        Comment.search_vector.match(squery),
                        User.search_vector.match(squery),
                    ),
                )
                .order_by(
                    db.desc(db.func.ts_rank_cd(Comment.search_vector, squery)),
                    db.desc(Comment.created_at),
                ),
                # Add query on future comment-supporting models here
            )
        )

    def profile_query(self, squery: str, profile: Profile) -> Query:
        """Search for comments within a profile."""
        return (
            Comment.query.join(User, Comment.user_id == User.id)
            .join(Project, Project.commentset_id == Comment.commentset_id)
            .filter(
                Project.profile == profile,
                Project.state.PUBLISHED,
                Comment.state.PUBLIC,
                db.or_(
                    Comment.search_vector.match(squery),
                    User.search_vector.match(squery),
                ),
            )
            .order_by(
                db.desc(db.func.ts_rank_cd(Comment.search_vector, squery)),
                db.desc(Comment.created_at),
            )
            .union_all(
                Comment.query.join(User, Comment.user_id == User.id)
                .join(Proposal, Proposal.commentset_id == Comment.commentset_id)
                .join(Project, Proposal.project_id == Project.id)
                .filter(
                    Project.profile == profile,
                    Project.state.PUBLISHED,
                    Comment.state.PUBLIC,
                    db.or_(
                        Comment.search_vector.match(squery),
                        User.search_vector.match(squery),
                    ),
                )
                .order_by(
                    db.desc(db.func.ts_rank_cd(Comment.search_vector, squery)),
                    db.desc(Comment.created_at),
                ),
                # Add query on future comment-supporting models here
            )
        )

    def project_query(self, squery: str, project: Project) -> Query:
        """Search for comments within a project."""
        return (
            Comment.query.join(User, Comment.user_id == User.id)
            .join(Commentset, Comment.commentset_id == Commentset.id)
            .filter(
                Commentset.id == project.commentset_id,
                Comment.state.PUBLIC,
                db.or_(
                    Comment.search_vector.match(squery),
                    User.search_vector.match(squery),
                ),
            )
            .order_by(
                db.desc(db.func.ts_rank_cd(Comment.search_vector, squery)),
                db.desc(Comment.created_at),
            )
            .union_all(
                Comment.query.join(User, Comment.user_id == User.id)
                .join(
                    Proposal,
                    db.and_(
                        Proposal.commentset_id == Comment.commentset_id,
                        Proposal.project_id == project.id,
                    ),
                )
                .filter(
                    Comment.state.PUBLIC,
                    db.or_(
                        Comment.search_vector.match(squery),
                        User.search_vector.match(squery),
                    ),
                )
                .order_by(
                    db.desc(db.func.ts_rank_cd(Comment.search_vector, squery)),
                    db.desc(Comment.created_at),
                ),
                # Add query on future comment-supporting models here
            )
        )


#: Ordered dictionary of search providers
search_providers = {
    'project': ProjectSearch(),
    'profile': ProfileSearch(),
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


def get_squery(text: Optional[str]) -> str:
    """
    Parse a web search query into a PostgreSQL ``tsquery``.

    This returns a text result instead of a SQL expression because SQLAlchemy's
    ``search_vector.match`` will render another ``to_tsquery`` call.

    This function requires ``websearch_to_tsquery`` from PostgreSQL >= 12.
    """
    return db.session.query(db.func.websearch_to_tsquery(text or '')).scalar()


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

    type: str
    label: str
    count: int
    job: Any


# @cache.memoize(timeout=300)
def search_counts(
    squery: str, profile: Optional[Profile] = None, project: Optional[Project] = None
) -> List[SearchCountType]:
    """
    Return counts of search results.

    This function requires an active request as it uses Flask-Executor to perform
    queries in parallel.
    """
    results: List[SearchCountType]
    if project is not None:
        results = [
            {
                'type': stype,
                'label': sp.label,
                'job': executor.submit(sp.project_count, squery, project),
            }
            for stype, sp in search_providers.items()
            if isinstance(sp, SearchInProjectProvider)
        ]
    elif profile is not None:
        results = [
            {
                'type': stype,
                'label': sp.label,
                'job': executor.submit(sp.profile_count, squery, profile),
            }
            for stype, sp in search_providers.items()
            if isinstance(sp, SearchInProfileProvider)
        ]
    else:
        # Not scoped to profile or project:
        results = [
            {
                'type': stype,
                'label': sp.label,
                'job': executor.submit(sp.all_count, squery),
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
    squery: str,
    stype: str,
    page=1,
    per_page=20,
    profile: Optional[Profile] = None,
    project: Optional[Project] = None,
):
    """Return search results."""
    # Pick up model data for the given type string
    sp = search_providers[stype]

    if project is not None:
        if not isinstance(sp, SearchInProjectProvider):
            raise TypeError(f"No project search for {sp.label}")
        query = sp.project_query(squery, project)
    elif profile is not None:
        if not isinstance(sp, SearchInProfileProvider):
            raise TypeError(f"No profile search for {sp.label}")
        query = sp.profile_query(squery, profile)
    else:
        query = sp.all_query(squery)

    # Add the three additional columns to the query and paginate results
    query = query.add_columns(
        sp.hltitle_column(squery),
        sp.hlsnippet_column(squery),
        sp.matched_text_column(squery),
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

    @route('/search')
    @render_with('search.html.jinja2', json=True)
    @requestargs(('q', abort_null), ('page', int), ('per_page', int))
    def search(self, q=None, page=1, per_page=20):
        """Perform site-level search."""
        squery = get_squery(q)
        # Can't use @requestargs for stype as it doesn't support name changes
        stype = abort_null(request.args.get('type'))
        if not squery:
            return redirect(url_for('index'))
        if stype is None or stype not in search_providers:
            return {'type': None, 'counts': search_counts(squery)}
        return {
            'type': stype,
            'counts': search_counts(squery),
            'results': search_results(squery, stype, page=page, per_page=per_page),
        }


SearchView.init_app(app)


@Profile.views('search')
@route('/<profile>')
class ProfileSearchView(ProfileViewMixin, UrlForView, ModelView):
    @route('search')
    @render_with('search.html.jinja2', json=True)
    @requires_roles({'reader', 'admin'})
    @requestargs(('q', abort_null), ('page', int), ('per_page', int))
    def search(self, q=None, page=1, per_page=20):
        """Perform search within a profile."""
        squery = get_squery(q)
        stype = abort_null(
            request.args.get('type')
        )  # Can't use requestargs as it doesn't support name changes
        if not squery:
            return redirect(url_for('index'))
        if (
            stype is None
            or stype not in search_providers
            or not isinstance(search_providers[stype], SearchInProfileProvider)
        ):
            return {'type': None, 'counts': search_counts(squery, profile=self.obj)}
        return {
            'profile': self.obj.current_access(datasets=('primary', 'related')),
            'type': stype,
            'counts': search_counts(squery, profile=self.obj),
            'results': search_results(
                squery, stype, page=page, per_page=per_page, profile=self.obj
            ),
        }


ProfileSearchView.init_app(app)


@Project.views('search')
@route('/<profile>/<project>/')
class ProjectSearchView(ProjectViewMixin, UrlForView, ModelView):
    @route('search')
    @render_with('search.html.jinja2', json=True)
    @requires_roles({'reader', 'crew', 'participant'})
    @requestargs(('q', abort_null), ('page', int), ('per_page', int))
    def search(self, q=None, page=1, per_page=20):
        """Perform search within a project."""
        squery = get_squery(q)
        stype = abort_null(
            request.args.get('type')
        )  # Can't use requestargs as it doesn't support name changes
        if not squery:
            return redirect(url_for('index'))
        if (
            stype is None
            or stype not in search_providers
            or not isinstance(search_providers[stype], SearchInProjectProvider)
        ):
            return {
                'project': self.obj.current_access(datasets=('primary', 'related')),
                'type': None,
                'counts': search_counts(squery, project=self.obj),
            }
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'type': stype,
            'counts': search_counts(squery, project=self.obj),
            'results': search_results(
                squery, stype, page=page, per_page=per_page, project=self.obj
            ),
        }


ProjectSearchView.init_app(app)
