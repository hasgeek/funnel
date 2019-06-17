# -*- coding: utf-8 -*-

from collections import OrderedDict, namedtuple
from flask import Markup, request, redirect, url_for
import sqlalchemy.sql.expression as expression
from coaster.utils import for_tsquery
from coaster.views import requestargs, render_with, route, ClassView
from baseframe import __
from ..models import db, Profile, Project, Proposal, Session, Comment
from .. import app, funnelapp


# --- Definitions -------------------------------------------------------------

# PostgreSQL ts_headline markers, picked for low probability of conflict with db content
pg_startsel = '<b>'
pg_stopsel = '</b>'
pg_delimiter = u' … '

# TODO: extend SearchModel to include profile_query_factory and project_query_factory
# for scoped search
SearchModel = namedtuple('SearchModel', ['label', 'model', 'has_title', 'query_factory'])

# The order here is preserved into the tabs shown in UI
search_types = OrderedDict([
    ('project', SearchModel(
        __("Projects"), Project, True,
        lambda: Project.all_unsorted())),
    ('profile', SearchModel(
        __("Profiles"), Profile, True,
        lambda: Profile.query)),
    ('session', SearchModel(
        __("Sessions"), Session, True,
        lambda: Session.query)),
    ('proposal', SearchModel(
        __("Proposals"), Proposal, True,
        lambda: Proposal.query)),
    ('comment', SearchModel(
        __("Comments"), Comment, False,
        lambda: Comment.query)),
    ])


# --- Utilities ---------------------------------------------------------------

def escape_quotes(text):
    """PostgreSQL strips tags for us, but to be completely safe we need to escape quotes"""
    return Markup(text.replace('"', '&quot;').replace("'", '&#39;'))


# --- Search functions --------------------------------------------------------

# @cache.memoize(timeout=300)
def search_counts(squery):
    """Return counts of search results"""
    return [{
        'type': k,
        'label': v.label,
        'count': v.query_factory().options(db.load_only(v.model.id)).filter(
            v.model.search_vector.match(squery)).count()}
        for k, v in search_types.items()]


# @cache.memoize(timeout=300)
def search_results(squery, stype, page=1, per_page=20):
    """Return search results"""
    # Pick up model data for the given type string
    st = search_types[stype]
    regconfig = st.model.search_vector.type.options.get('regconfig', 'english')

    # Construct a basic query, sorted by matching column priority followed by date.
    # TODO: Pick the right query factory depending on requested scoping.
    # TODO: Pick a better date column than "created_at".
    query = st.query_factory().filter(
        st.model.search_vector.match(squery)).order_by(
            db.desc(db.func.ts_rank_cd(st.model.search_vector, squery)), st.model.created_at.desc())

    # Show rich summary by including the item's title with search terms highlighted
    # (only if the item has a title)
    if st.has_title:
        title_column = db.func.ts_headline(
            regconfig,
            st.model.title,
            db.func.to_tsquery(squery),
            'HighlightAll=TRUE, StartSel="%s", StopSel="%s"' % (pg_startsel, pg_stopsel),
            type_=db.UnicodeText
            )
    else:
        title_column = expression.null()

    if 'hltext' in st.model.search_vector.type.options:
        hltext = st.model.search_vector.type.options['hltext']()
    else:
        hltext = db.func.concat_ws(
            ' / ', *(getattr(st.model, c) for c in st.model.search_vector.type.columns))

    # Also show a snippet of the item's text with search terms highlighted
    # Because we are searching against raw Markdown instead of rendered HTML,
    # the snippet will be somewhat bland. We can live with it for now.
    snippet_column = db.func.ts_headline(
        regconfig,
        hltext,
        db.func.to_tsquery(squery),
        'MaxFragments=2, FragmentDelimiter="%s", '
        'MinWords=5, MaxWords=20, '
        'StartSel="%s", StopSel="%s"' % (pg_delimiter, pg_startsel, pg_stopsel),
        type_=db.UnicodeText
        )

    # Add the two additional columns to the query and paginate results
    query = query.add_columns(title_column, snippet_column)
    pagination = query.paginate(page=page, per_page=per_page, max_per_page=100)

    # Return a page of results
    return {
        'items': [{
            'title': escape_quotes(title) if title is not None else None,
            'url': item.absolute_url,
            'snippet': escape_quotes(snippet),
            'obj': dict(item.current_access()),
            } for item, title, snippet in pagination.items],
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
    @route('/search')
    @render_with('search.html.jinja2', json=True)
    @requestargs('q', ('page', int), ('per_page', int))
    def search(self, q=None, page=1, per_page=20):
        squery = for_tsquery(q or '')
        stype = request.args.get('type')  # Can't use requestargs as it doesn't support name changes
        if not squery:
            return redirect(url_for('index'))
        if stype is None or stype not in search_types:
            return {
                'type': None,
                'counts': search_counts(squery)
                }
        else:
            return {
                'type': stype,
                'counts': search_counts(squery),
                'results': search_results(squery, stype, page=page, per_page=per_page)
                }


SearchView.init_app(app)
SearchView.init_app(funnelapp)
