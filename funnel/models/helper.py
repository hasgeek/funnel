# -*- coding: utf-8 -*-

from sqlalchemy_searchable import SearchQueryMixin
from coaster.sqlalchemy import Query

__all__ = ['RESERVED_NAMES', 'SearchQuery']


RESERVED_NAMES = set([
    '_baseframe',
    'admin',
    'api',
    'app',
    'apps',
    'auth',
    'blog',
    'boxoffice',
    'brand',
    'brands',
    'client',
    'clients',
    'confirm',
    'delete',
    'edit',
    'email'
    'emails'
    'embed',
    'event',
    'events',
    'ftp',
    'funnel',
    'funnels',
    'hacknight',
    'hacknights',
    'hasjob',
    'hgtv',
    'imap',
    'kharcha',
    'login',
    'logout',
    'new',
    'news',
    'organization',
    'organizations',
    'org',
    'orgs',
    'pop',
    'pop3',
    'post',
    'posts',
    'profile',
    'profiles',
    'project',
    'projects',
    'proposal',
    'proposals',
    'register',
    'reset',
    'search',
    'smtp',
    'static',
    'ticket',
    'tickets',
    'token',
    'tokens',
    'venue',
    'venues',
    'video',
    'videos',
    'workshop',
    'workshops',
    'www',
    ])


class SearchQuery(Query, SearchQueryMixin):
    """Adds Model.query.search"""
    pass
