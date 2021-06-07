from collections import OrderedDict, namedtuple
from html import unescape as html_unescape
from typing import Optional
from urllib.parse import quote as urlquote
import re

import sqlalchemy.sql.expression as expression

from flask import Markup, redirect, request, url_for

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

from .. import app
from ..models import (
    Comment,
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

# --- Definitions -------------------------------------------------------------

# PostgreSQL ts_headline markers
pg_startsel = '<b>'
pg_stopsel = '</b>'
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

SearchModel = namedtuple(
    'SearchModel',
    [
        'label',
        'model',
        'has_title',
        'has_order',
        'all_query_filter',
        'profile_query_filter',
        'project_query_filter',
    ],
)

# The order here is preserved into the tabs shown in UI
search_types = OrderedDict(
    [
        (
            'project',
            SearchModel(
                __("Projects"),
                Project,
                True,  # has a title column
                True,  # has order_by in the queries here; don't bother to order again
                # Site search:
                lambda q: Project.query.join(Profile).filter(
                    Profile.state.PUBLIC,
                    Project.state.PUBLISHED,
                    db.or_(
                        # Search conditions. Any of:
                        # 1. Project has search terms
                        Project.search_vector.match(q),
                        # 2. Project's profile (for org) has a match in the org title
                        Organization.query.filter(
                            Project.profile_id == Profile.id,
                            Profile.organization_id == Organization.id,
                            Organization.search_vector.match(q),
                        ).exists(),
                        # 3. Project's profile (for user) has a match in the user's name
                        User.query.filter(
                            Project.profile_id == Profile.id,
                            Profile.user_id == User.id,
                            User.search_vector.match(q),
                        ).exists(),
                        # 4. Update has search terms
                        Update.query.filter(
                            Update.project_id == Project.id,
                            Update.search_vector.match(q),
                        ).exists(),
                    ),
                )
                # TODO: Replace `start_at` in distance with a new `nearest_session_at`.
                # The existing `next_session_at` is not suitable as it is future-only.
                # Also add a CHECK constraint on session.start_at/end_at to enforce 24
                # hour max duration.
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
                    db.desc(db.func.ts_rank_cd(Project.search_vector, q)),
                ),
                # Profile search:
                lambda q, profile: Project.query.join(Profile)
                .filter(
                    Project.profile == profile,
                    Project.state.PUBLISHED,
                    db.or_(
                        # Search conditions. Any of:
                        # 1. Project has search terms
                        Project.search_vector.match(q),
                        # 2. Update has search terms
                        Update.query.filter(
                            Update.project_id == Project.id,
                            Update.search_vector.match(q),
                        ).exists(),
                    ),
                )
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
                    db.desc(db.func.ts_rank_cd(Project.search_vector, q)),
                ),
                # No project search inside projects:
                None,
            ),
        ),
        (
            'profile',
            SearchModel(
                __("Profiles"),
                Profile,
                True,
                False,
                lambda q: Profile.query.filter(
                    Profile.state.PUBLIC,
                    db.or_(
                        Profile.search_vector.match(q),
                        User.query.filter(
                            Profile.user_id == User.id, User.search_vector.match(q)
                        ).exists(),
                        Organization.query.filter(
                            Profile.organization_id == Organization.id,
                            Organization.search_vector.match(q),
                        ).exists(),
                    ),
                ),
                # No profile search inside profiles:
                None,
                # No profile search inside projects:
                None,
            ),
        ),
        (
            'session',
            SearchModel(
                __("Sessions"),
                Session,
                True,
                False,
                # Site search:
                lambda q: Session.query.join(Project, Session.project)
                .join(Profile, Project.profile)
                .outerjoin(Proposal, Session.proposal)
                .filter(
                    Profile.state.PUBLIC,
                    Project.state.PUBLISHED,
                    Session.scheduled,
                    Session.search_vector.match(q),
                ),
                # Profile search:
                lambda q, profile: Session.query.join(Project, Session.project)
                .outerjoin(Proposal, Session.proposal)
                .filter(
                    Project.state.PUBLISHED,
                    Project.profile == profile,
                    Session.scheduled,
                    Session.search_vector.match(q),
                ),
                # Project search:
                lambda q, project: Session.query.outerjoin(Proposal).filter(
                    Session.project == project,
                    Session.scheduled,
                    Session.search_vector.match(q),
                ),
            ),
        ),
        (
            'proposal',
            SearchModel(
                __("Submissions"),
                Proposal,
                True,
                False,
                # Site search:
                lambda q: Proposal.query.join(Project, Proposal.project)
                .join(Profile, Project.profile)
                .filter(
                    Profile.state.PUBLIC,
                    Project.state.PUBLISHED,
                    # TODO: Filter condition for Proposal being visible.
                    # Dependent on proposal editorial workflow states being completely
                    # transferred into labels, reserving proposal state for submission.
                    db.or_(
                        Proposal.search_vector.match(q),
                        ProposalMembership.query.join(User, ProposalMembership.user)
                        .filter(
                            ProposalMembership.proposal_id == Proposal.id,
                            ProposalMembership.user_id == User.id,
                            ProposalMembership.is_uncredited.is_(False),
                            ProposalMembership.is_active,
                            User.search_vector.match(q),
                        )
                        .exists()
                        .correlate(Proposal),
                    ),
                ),
                # Profile search
                lambda q, profile: Proposal.query.join(
                    Project, Proposal.project
                ).filter(
                    Project.state.PUBLISHED,
                    Project.profile == profile,
                    # TODO: Filter condition for Proposal being visible
                    db.or_(
                        Proposal.search_vector.match(q),
                        ProposalMembership.query.join(User, ProposalMembership.user)
                        .filter(
                            ProposalMembership.proposal_id == Proposal.id,
                            ProposalMembership.user_id == User.id,
                            ProposalMembership.is_uncredited.is_(False),
                            ProposalMembership.is_active,
                            User.search_vector.match(q),
                        )
                        .exists()
                        .correlate(Proposal),
                    ),
                ),
                # Project search:
                lambda q, project: Proposal.query.filter(
                    Proposal.project == project,
                    # TODO: Filter condition for Proposal being visible
                    db.or_(
                        Proposal.search_vector.match(q),
                        ProposalMembership.query.join(User, ProposalMembership.user)
                        .filter(
                            ProposalMembership.proposal_id == Proposal.id,
                            ProposalMembership.user_id == User.id,
                            ProposalMembership.is_uncredited.is_(False),
                            ProposalMembership.is_active,
                            User.search_vector.match(q),
                        )
                        .exists()
                        .correlate(Proposal),
                    ),
                ),
            ),
        ),
        (
            'comment',
            SearchModel(
                __("Comments"),
                Comment,
                False,  # Comments don't have titles
                True,  # Queries return ordered results
                # Site search:
                lambda q: Comment.query.join(User, Comment.user)
                .join(Project, Project.commentset_id == Comment.commentset_id)
                .join(Profile, Project.profile_id == Profile.id)
                .filter(
                    Profile.state.PUBLIC,
                    Project.state.PUBLISHED,
                    Comment.state.PUBLIC,
                    db.or_(Comment.search_vector.match(q), User.search_vector.match(q)),
                )
                .order_by(
                    db.desc(db.func.ts_rank_cd(Comment.search_vector, q)),
                    db.desc(Comment.created_at),
                )
                .union_all(
                    Comment.query.join(User)
                    .join(Proposal, Proposal.commentset_id == Comment.commentset_id)
                    .join(Project, Proposal.project_id == Project.id)
                    .join(Profile, Project.profile_id == Profile.id)
                    .filter(
                        Profile.state.PUBLIC,
                        Project.state.PUBLISHED,
                        Comment.state.PUBLIC,
                        db.or_(
                            Comment.search_vector.match(q), User.search_vector.match(q)
                        ),
                    )
                    .order_by(
                        db.desc(db.func.ts_rank_cd(Comment.search_vector, q)),
                        db.desc(Comment.created_at),
                    ),
                    # Add query on Post model here
                ),
                # Profile search:
                lambda q, profile: Comment.query.join(User, Comment.user)
                .join(Project, Project.commentset_id == Comment.commentset_id)
                .filter(
                    Project.profile == profile,
                    Project.state.PUBLISHED,
                    Comment.state.PUBLIC,
                    db.or_(Comment.search_vector.match(q), User.search_vector.match(q)),
                )
                .order_by(
                    db.desc(db.func.ts_rank_cd(Comment.search_vector, q)),
                    db.desc(Comment.created_at),
                )
                .union_all(
                    Comment.query.join(User)
                    .join(Proposal, Proposal.commentset_id == Comment.commentset_id)
                    .join(Project, Proposal.project_id == Project.id)
                    .filter(
                        Project.profile == profile,
                        Project.state.PUBLISHED,
                        Comment.state.PUBLIC,
                        db.or_(
                            Comment.search_vector.match(q), User.search_vector.match(q)
                        ),
                    )
                    .order_by(
                        db.desc(db.func.ts_rank_cd(Comment.search_vector, q)),
                        db.desc(Comment.created_at),
                    ),
                    # Add query on Post model here
                ),
                # Project search:
                lambda q, project: Comment.query.join(User, Comment.user)
                .join(Project, project.commentset_id == Comment.commentset_id)
                .filter(
                    Comment.state.PUBLIC,
                    db.or_(Comment.search_vector.match(q), User.search_vector.match(q)),
                )
                .order_by(
                    db.desc(db.func.ts_rank_cd(Comment.search_vector, q)),
                    db.desc(Comment.created_at),
                )
                .union_all(
                    Comment.query.join(User)
                    .join(Proposal, Proposal.commentset_id == Comment.commentset_id)
                    .join(Project, Proposal.project_id == project.id)
                    .filter(
                        Comment.state.PUBLIC,
                        db.or_(
                            Comment.search_vector.match(q), User.search_vector.match(q)
                        ),
                    )
                    .order_by(
                        db.desc(db.func.ts_rank_cd(Comment.search_vector, q)),
                        db.desc(Comment.created_at),
                    ),
                    # Add query on Post model here
                ),
            ),
        ),
    ]
)


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
    return urlquote(
        html_unescape(
            html_whitespace_re.sub(' ', match_text_breakpoint_re.sub('', text)).strip()
        )
    )


# --- Search functions --------------------------------------------------------

# @cache.memoize(timeout=300)
def search_counts(
    squery: str, profile: Optional[Profile] = None, project: Optional[Project] = None
):
    """Return counts of search results."""
    if project is not None:
        return [
            {
                'type': k,
                'label': v.label,
                'count': v.project_query_filter(squery, project)
                .options(db.load_only(v.model.id))
                .count(),
            }
            for k, v in search_types.items()
            if v.project_query_filter is not None
        ]
    if profile is not None:
        return [
            {
                'type': k,
                'label': v.label,
                'count': v.profile_query_filter(squery, profile)
                .options(db.load_only(v.model.id))
                .count(),
            }
            for k, v in search_types.items()
            if v.profile_query_filter is not None
        ]
    # Not scoped to profile or project:
    return [
        {
            'type': k,
            'label': v.label,
            'count': v.all_query_filter(squery)
            .options(db.load_only(v.model.id))
            .count(),
        }
        for k, v in search_types.items()
    ]


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
    st = search_types[stype]
    regconfig = st.model.search_vector.type.options.get('regconfig', 'english')

    # Construct a basic query, sorted by matching column priority followed by date.
    # TODO: Pick a better date column than "created_at".
    if project is not None:
        query = st.project_query_filter(squery, project)
        if not st.has_order:
            query = query.order_by(
                db.desc(db.func.ts_rank_cd(st.model.search_vector, squery)),
                st.model.created_at.desc(),
            )
    elif profile is not None:
        query = st.profile_query_filter(squery, profile)
        if not st.has_order:
            query = query.order_by(
                db.desc(db.func.ts_rank_cd(st.model.search_vector, squery)),
                st.model.created_at.desc(),
            )
    else:
        query = st.all_query_filter(squery)
        if not st.has_order:
            query = query.order_by(
                db.desc(db.func.ts_rank_cd(st.model.search_vector, squery)),
                st.model.created_at.desc(),
            )

    # Show rich summary by including the item's title with search terms highlighted
    # (only if the item has a title)
    if st.has_title:
        title_column = db.func.ts_headline(
            regconfig,
            st.model.title,
            db.func.to_tsquery(squery),
            'HighlightAll=TRUE, StartSel="%s", StopSel="%s"'
            % (pg_startsel, pg_stopsel),
            type_=db.UnicodeText,
        )
    else:
        title_column = expression.null()

    if 'hltext' in st.model.search_vector.type.options:
        hltext = st.model.search_vector.type.options['hltext']()
    else:
        hltext = db.func.concat_ws(
            visual_field_delimiter,
            *(getattr(st.model, c) for c in st.model.search_vector.type.columns),
        )

    # Also show a snippet of the item's text with search terms highlighted
    # Because we are searching against raw Markdown instead of rendered HTML,
    # the snippet will be somewhat bland. We can live with it for now.
    snippet_column = db.func.ts_headline(
        regconfig,
        hltext,
        db.func.to_tsquery(squery),
        'MaxFragments=2, FragmentDelimiter="%s",'
        ' MinWords=5, MaxWords=20,'
        ' StartSel="%s", StopSel="%s"' % (pg_delimiter, pg_startsel, pg_stopsel),
        type_=db.UnicodeText,
    )

    matched_text_column = db.func.ts_headline(
        regconfig,
        hltext,
        db.func.to_tsquery(squery),
        'MaxFragments=0, MaxWords=100, StartSel="", StopSel=""',
        type_=db.UnicodeText,
    )

    # Add the two additional columns to the query and paginate results
    query = query.add_columns(title_column, snippet_column, matched_text_column)
    pagination = query.paginate(page=page, per_page=per_page, max_per_page=100)

    # Return a page of results
    return {
        'items': [
            {
                'title': item.title if st.has_title else None,
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
        squery = get_squery(q)
        stype = abort_null(
            request.args.get('type')
        )  # Can't use requestargs as it doesn't support name changes
        if not squery:
            return redirect(url_for('index'))
        if stype is None or stype not in search_types:
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
        squery = get_squery(q)
        stype = abort_null(
            request.args.get('type')
        )  # Can't use requestargs as it doesn't support name changes
        if not squery:
            return redirect(url_for('index'))
        if (
            stype is None
            or stype not in search_types
            or search_types[stype].profile_query_filter is None
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
        squery = get_squery(q)
        stype = abort_null(
            request.args.get('type')
        )  # Can't use requestargs as it doesn't support name changes
        if not squery:
            return redirect(url_for('index'))
        if (
            stype is None
            or stype not in search_types
            or search_types[stype].project_query_filter is None
        ):
            return {'type': None, 'counts': search_counts(squery, project=self.obj)}
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'type': stype,
            'counts': search_counts(squery, project=self.obj),
            'results': search_results(
                squery, stype, page=page, per_page=per_page, project=self.obj
            ),
        }


ProjectSearchView.init_app(app)
