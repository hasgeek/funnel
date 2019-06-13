# -*- coding: utf-8 -*-

from collections import OrderedDict, namedtuple
from flask import Markup, request, escape
import sqlalchemy.sql.expression as expression
from coaster.utils import for_tsquery
from coaster.views import render_with, route, ClassView
from baseframe import __
from ..models import db, Profile, Project, Label, Proposal, Session, Comment
from .. import app, funnelapp

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
    ('label', SearchModel(
        __("Labels"), Label, True,
        lambda: Label.query)),
    ])


class SearchView(ClassView):
    startsel = "{{{{{[[[[["
    stopsel = "]]]]]}}}}}"

    def highlight_snippet(self, text):
        return escape(text).replace(self.startsel, Markup('<b>')).replace(self.stopsel, Markup('</b>'))

    def search_counts(self, squery):
        """Return counts of search results"""
        return [{
            'type': k,
            'label': v.label,
            'count': v.query_factory().filter(v.model.search_vector.match(squery)).count()}
            for k, v in search_types.items()]

    def search_results(self, squery, stype):
        """Return search results"""
        def intersperse_spaces(iterable):
            # From https://stackoverflow.com/a/5656097/78903
            it = iter(iterable)
            yield next(it)
            for x in it:
                yield ' '
                yield x

        st = search_types[stype]
        regconfig = st.model.search_vector.type.options.get('regconfig', 'english')

        query = st.query_factory().filter(
            st.model.search_vector.match(squery)).order_by(
                db.desc(db.func.ts_rank_cd(st.model.search_vector, squery)))
        if st.has_title:
            title_column = db.func.ts_headline(
                regconfig,
                st.model.title,
                db.func.to_tsquery(squery),
                'HighlightAll=TRUE, StartSel="%s", StopSel="%s"' % (self.startsel, self.stopsel),
                type_=db.UnicodeText
                )
        else:
            title_column = expression.null()

        snippet_column = db.func.ts_headline(
            regconfig,
            db.func.concat(*intersperse_spaces(
                getattr(st.model, c) for c in st.model.search_vector.type.columns)),
            db.func.to_tsquery(squery),
            'MaxFragments=5, FragmentDelimiter=|||, '
            'StartSel="%s", StopSel="%s"' % (self.startsel, self.stopsel),
            type_=db.UnicodeText
            )

        query = query.add_columns(title_column, snippet_column)
        pagination = query.paginate(max_per_page=100)

        return {
            'items': [{
                'title': self.highlight_snippet(title) if title is not None else None,
                'url': item.absolute_url,
                'snippets': self.highlight_snippet(snippet).split('|||'),
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

    @route('/search')
    @render_with(json=True)
    def search(self):
        squery = for_tsquery(request.args.get('q'))
        stype = request.args.get('type')
        if not squery:
            return {}
        if stype is None or stype not in search_types:
            return {
                'type': None,
                'counts': self.search_counts(squery)
                }
        else:
            return {
                'type': stype,
                'counts': self.search_counts(squery),
                'results': self.search_results(squery, stype)
                }


SearchView.init_app(app)
SearchView.init_app(funnelapp)
