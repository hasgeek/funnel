from textwrap import dedent
import re

from sqlalchemy import DDL, event
from sqlalchemy.dialects.postgresql.base import (
    RESERVED_WORDS as POSTGRESQL_RESERVED_WORDS,
)

from zxcvbn import zxcvbn

__all__ = [
    'RESERVED_NAMES',
    'password_policy',
    'add_to_class',
    'add_search_trigger',
    'visual_field_delimiter',
    'add_search_trigger',
    'password_policy',
    'valid_name',
    'valid_username',
]


RESERVED_NAMES = {
    '_baseframe',
    'about',
    'account',
    'admin',
    'api',
    'app',
    'apps',
    'auth',
    'blog',
    'boxoffice',
    'brand',
    'brands',
    'by',
    'client',
    'clients',
    'comments',
    'confirm',
    'contact',
    'contacts',
    'crew',
    'dashboard',
    'delete',
    'edit',
    'email',
    'emails',
    'embed',
    'event',
    'events',
    'ftp',
    'funnel',
    'funnels',
    'hacknight',
    'hacknights',
    'hgtv',
    'imap',
    'in',
    'json',
    'kharcha',
    'login',
    'logout',
    'members',
    'membership',
    'new',
    'news',
    'notification',
    'notifications',
    'org',
    'organization',
    'organizations',
    'orgs',
    'pop',
    'pop3',
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
    'update',
    'updates',
    'venue',
    'venues',
    'video',
    'videos',
    'workshop',
    'workshops',
    'www',
}


class PasswordPolicy:
    def __init__(self, min_length, min_score):
        self.min_length = min_length
        self.min_score = min_score

    def test_password(self, password, user_inputs=None):
        result = zxcvbn(password, user_inputs)
        return {
            'is_weak': (
                len(password) < self.min_length
                or result['score'] < self.min_score
                or bool(result['feedback']['warning'])
            ),
            'score': result['score'],
            'warning': result['feedback']['warning'],
            'suggestions': result['feedback']['suggestions'],
        }


# Strong passwords require a strength of at least 3 as per the zxcvbn
# project documentation.
password_policy = PasswordPolicy(min_length=8, min_score=3)

# re.IGNORECASE needs re.ASCII because of a quirk in the characters it matches.
# https://docs.python.org/3/library/re.html#re.I
_username_valid_re = re.compile('^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', re.I | re.A)
_name_valid_re = re.compile('^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', re.A)


visual_field_delimiter = ' ¦ '


def add_to_class(cls, name=None):
    """
    Decorator to add a new method to a class. Takes an optional attribute name.

    Usage::

        @add_to_class(ExistingClass)
        def new_method(self, *args):
            pass

        @add_to_class(ExistingClass, 'new_property_name')
        @property
        def existing_class_new_property(self):
            pass
    """

    def decorator(attr):
        use_name = name or attr.__name__
        if use_name in cls.__dict__:
            raise AttributeError(f"{cls.__name__} already has attribute {use_name}")
        setattr(cls, use_name, attr)
        return attr

    return decorator


def reopen(cls):
    """
    Copies the contents of the decorated class into an existing class and returns it.

    Usage::

        @reopen(ExistingClass)
        class ExistingClass:
            def new_method(self, *args):
                pass
    """

    def decorator(new_cls):
        for attr, value in new_cls.__dict__.items():
            if attr not in (
                '__dict__',
                '__doc__',
                '__module__',
                '__slots__',
                '__weakref__',
            ):
                if hasattr(cls, attr):
                    raise AttributeError(f"{cls.__name__} already has attribute {attr}")
                setattr(cls, attr, value)
        return cls

    return decorator


def valid_username(candidate):
    """
    Check if a username is valid. Letters, numbers and non-terminal hyphens only.
    """
    return not _username_valid_re.search(candidate) is None


def valid_name(candidate):
    """
    Check if a name is valid. Lowercase letters, numbers and non-terminal hyphens only.
    """
    return not _name_valid_re.search(candidate) is None


def pgquote(identifier):
    """
    Adds double quotes to the given identifier if required (PostgreSQL only).
    """
    return (
        ('"%s"' % identifier) if identifier in POSTGRESQL_RESERVED_WORDS else identifier
    )


def add_search_trigger(model, column_name):
    """
    Adds a search trigger and returns SQL for use in migrations. Typical use::

        class MyModel(db.Model):
            ...
            search_vector = db.deferred(db.Column(
                TSVectorType(
                    'name', 'title', *indexed_columns,
                    weights={'name': 'A', 'title': 'B'},
                    regconfig='english'
                ),
                nullable=False,
            ))

            __table_args__ = (
                db.Index(
                    'ix_mymodel_search_vector',
                    'search_vector',
                    postgresql_using='gin'
                ),
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
            regconfig=regconfig, col=pgquote(col)
        )
        uexpr = "to_tsvector('{regconfig}', COALESCE({col}, ''))".format(
            regconfig=regconfig, col=pgquote(col)
        )
        if col in weights:
            texpr = "setweight({expr}, '{weight}')".format(
                expr=texpr, weight=weights[col]
            )
            uexpr = "setweight({expr}, '{weight}')".format(
                expr=uexpr, weight=weights[col]
            )
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
        '''.format(  # nosec
            function_name=pgquote(function_name),
            column_name=pgquote(column_name),
            trigger_expr=trigger_expr,
            trigger_name=pgquote(trigger_name),
            table_name=pgquote(model.__tablename__),
        )
    )

    update_statement = dedent(
        '''
        UPDATE {table_name} SET {column_name} = {update_expr};
        '''.format(  # nosec
            table_name=pgquote(model.__tablename__),
            column_name=pgquote(column_name),
            update_expr=update_expr,
        )
    )

    drop_statement = dedent(
        '''
        DROP TRIGGER {trigger_name} ON {table_name};
        DROP FUNCTION {function_name}();
        '''.format(  # nosec
            trigger_name=pgquote(trigger_name),
            table_name=pgquote(model.__tablename__),
            function_name=pgquote(function_name),
        )
    )

    event.listen(
        model.__table__,
        'after_create',
        DDL(trigger_function).execute_if(dialect='postgresql'),
    )

    event.listen(
        model.__table__,
        'before_drop',
        DDL(drop_statement).execute_if(dialect='postgresql'),
    )

    return {
        'trigger': trigger_function,
        'update': update_statement,
        'drop': drop_statement,
    }
