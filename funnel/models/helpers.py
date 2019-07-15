# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from textwrap import dedent

from sqlalchemy import DDL, event
from sqlalchemy.dialects.postgresql.base import (
    RESERVED_WORDS as POSTGRESQL_RESERVED_WORDS,
)

__all__ = ['RESERVED_NAMES', 'add_search_trigger']


RESERVED_NAMES = {
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
    'contact',
    'contacts',
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
}


def pgquote(identifier):
    """
    Adds double quotes to the given identifier if required (PostgreSQL only).
    """
    return ('"%s"' % identifier) if identifier in POSTGRESQL_RESERVED_WORDS else identifier


def add_search_trigger(model, column_name):
    """
    Adds a search trigger and returns SQL for use in migrations. Typical use::

        class MyModel(db.Model):
            ...
            search_vector = db.deferred(db.Column(
                TSVectorType('name', 'title', weights={'name': 'A', 'title': 'B'}, regconfig='english'),
                nullable=False))

            __table_args__ = (
                db.Index('ix_mymodel_search_vector', 'search_vector', postgresql_using='gin'),
                )

        add_search_trigger(MyModel, 'search_vector')

    To extract the SQL required in a migration:

        $ python manage.py shell
        >>> print(models.add_search_trigger(models.MyModel, 'search_vector')['trigger'])

    Available keys: ``update``, ``trigger`` (for upgrades) and ``drop`` (for downgrades).

    :param model: Model class
    :param str column_name: Name of the tsvector column in the model
    """
    column = getattr(model, column_name)
    function_name = model.__tablename__ + '_' + column_name + '_update'
    trigger_name = model.__tablename__ + '_' + column_name + '_trigger'
    weights = column.type.options.get('weights', {})
    regconfig = column.type.options.get('regconfig', 'english')

    trigger_fields = []
    update_fields = []

    for col in column.type.columns:
        texpr = "to_tsvector('{regconfig}', COALESCE(NEW.{col}, ''))".format(
            regconfig=regconfig, col=pgquote(col))
        uexpr = "to_tsvector('{regconfig}', COALESCE({col}, ''))".format(
            regconfig=regconfig, col=pgquote(col))
        if col in weights:
            texpr = "setweight({expr}, '{weight}')".format(expr=texpr, weight=weights[col])
            uexpr = "setweight({expr}, '{weight}')".format(expr=uexpr, weight=weights[col])
        trigger_fields.append(texpr)
        update_fields.append(uexpr)

    trigger_expr = ' || '.join(trigger_fields)
    update_expr = ' || '.join(update_fields)

    trigger_function = dedent(
        '''
        CREATE FUNCTION {function_name}() RETURNS trigger AS $$
        BEGIN
            NEW.{column_name} := {trigger_expr};
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER {trigger_name} BEFORE INSERT OR UPDATE ON {table_name}
        FOR EACH ROW EXECUTE PROCEDURE {function_name}();
        '''.format(
            function_name=pgquote(function_name),
            column_name=pgquote(column_name),
            trigger_expr=trigger_expr,
            trigger_name=pgquote(trigger_name),
            table_name=pgquote(model.__tablename__),
            ))

    update_statement = dedent(
        '''
        UPDATE {table_name} SET {column_name} = {update_expr};
        '''.format(
            table_name=pgquote(model.__tablename__),
            column_name=pgquote(column_name),
            update_expr=update_expr,
            ))

    drop_statement = dedent(
        '''
        DROP TRIGGER {trigger_name} ON {table_name};
        DROP FUNCTION {function_name}();
        '''.format(
            trigger_name=pgquote(trigger_name),
            table_name=pgquote(model.__tablename__),
            function_name=pgquote(function_name),
            ))

    event.listen(model.__table__, 'after_create',
        DDL(trigger_function).execute_if(dialect='postgresql'))

    event.listen(model.__table__, 'before_drop',
        DDL(drop_statement).execute_if(dialect='postgresql'))

    return {
        'trigger': trigger_function,
        'update': update_statement,
        'drop': drop_statement,
        }
