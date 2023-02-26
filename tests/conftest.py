"""Test configuration and fixtures."""
# pylint: disable=import-outside-toplevel, redefined-outer-name

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import unified_diff
from types import MethodType, SimpleNamespace
from unittest.mock import patch
import re
import shutil
import typing as t

from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.session import Session as FsaSession
from sqlalchemy.orm import Session as DatabaseSessionClass
import sqlalchemy as sa

import pytest

if t.TYPE_CHECKING:
    from flask import Flask
    from flask.testing import FlaskClient

    import funnel.models as funnel_models


# --- Pytest config --------------------------------------------------------------------


def pytest_addoption(parser) -> None:
    """Allow db_session to be configured in the command line."""
    parser.addoption(
        '--dbsession',
        action='store',
        default='rollback',
        choices=('rollback', 'truncate'),
        help="Use db_session with 'rollback' (default) or 'truncate'"
        " (slower but more production-like)",
    )


def pytest_collection_modifyitems(items) -> None:
    """Sort tests to run lower level before higher level."""
    test_order = (
        'tests/unit/models',
        'tests/unit/forms',
        'tests/unit/proxies',
        'tests/unit/transports',
        'tests/unit/views',
        'tests/unit',
        'tests/integration/views',
        'tests/integration',
        'tests/features',
        'tests/e2e',
    )

    def sort_key(item) -> t.Tuple[int, str]:
        module_file = item.module.__file__
        for counter, path in enumerate(test_order):
            if path in module_file:
                return (counter, module_file)
        return (-1, module_file)

    items.sort(key=sort_key)


# --- Import fixtures ------------------------------------------------------------------


@pytest.fixture(scope='session')
def funnel():
    """Funnel package."""
    return pytest.importorskip('funnel')


@pytest.fixture(scope='session')
def models(funnel):
    """Funnel models package."""
    return pytest.importorskip('funnel.models')


@pytest.fixture(scope='session')
def forms(funnel):
    """Funnel forms package."""
    return pytest.importorskip('funnel.forms')


@pytest.fixture(scope='session')
def views(funnel):
    """Funnel views package."""
    return pytest.importorskip('funnel.views')


@pytest.fixture(scope='session')
def funnel_devtest(funnel):
    """Return devtest module as a fixture."""
    return pytest.importorskip('funnel.devtest')


# --- Fixtures -------------------------------------------------------------------------


@pytest.fixture(scope='session')
def response_with_forms() -> t.Any:  # Since the actual return type is defined within
    from flask.wrappers import Response

    from lxml.html import FormElement, HtmlElement, fromstring  # nosec

    # --- ResponseWithForms, to make form submission in the test client testing easier
    # --- Adapted from the abandoned Flask-Fillin package

    _meta_refresh_content_re = re.compile(
        r"""
        \s*
        (?P<timeout>\d+)      # Timeout
        \s*
        ;?                    # ; separator for optional URL
        \s*
        (?:URL\s*=\s*["']?)?  # Optional 'URL=' or 'URL="' prefix
        (?P<url>.*?)          # Optional URL
        (?:["']?\s*)          # Optional closing quote for URL
        """,
        re.ASCII | re.IGNORECASE | re.VERBOSE,
    )

    class MetaRefreshContent(t.NamedTuple):
        """Timeout and optional URL in a Meta Refresh tag."""

        timeout: int
        url: t.Optional[str] = None

    class ResponseWithForms(Response):
        """
        Wrapper for the test client response that makes form submission easier.

        Usage::

            def test_mytest(client) -> None:
                response = client.get('/page_with_forms')
                form = response.form('login')
                form.fields['username'] = 'my username'
                form.fields['password'] = 'secret'
                form.fields['remember'] = True
                next_response = form.submit(client)
        """

        _parsed_html: t.Optional[HtmlElement] = None

        @property
        def html(self) -> HtmlElement:
            """Return the parsed HTML tree."""
            if self._parsed_html is None:
                self._parsed_html = fromstring(self.data)

                # add click method to all links
                def _click(
                    self, client, **kwargs
                ) -> None:  # pylint: disable=redefined-outer-name
                    # `self` is the `a` element here
                    path = self.attrib['href']
                    return client.get(path, **kwargs)

                for link in self._parsed_html.iter('a'):
                    link.click = MethodType(_click, link)  # type: ignore[attr-defined]

                # add submit method to all forms
                def _submit(
                    self, client, path=None, **kwargs
                ) -> None:  # pylint: disable=redefined-outer-name
                    # `self` is the `form` element here
                    data = dict(self.form_values())
                    if 'data' in kwargs:
                        data.update(kwargs['data'])
                        del kwargs['data']
                    if path is None:
                        path = self.action
                    if 'method' not in kwargs:
                        kwargs['method'] = self.method
                    return client.open(path, data=data, **kwargs)

                for form in self._parsed_html.forms:  # type: ignore[attr-defined]
                    form.submit = MethodType(_submit, form)
            return self._parsed_html

        @property
        def forms(self) -> t.List[FormElement]:
            """
            Return list of all forms in the document.

            Contains the LXML form type as documented at
            http://lxml.de/lxmlhtml.html#forms with an additional `.submit(client)`
            method to submit the form.
            """
            return self.html.forms

        def form(
            self, id_: t.Optional[str] = None, name: t.Optional[str] = None
        ) -> t.Optional[FormElement]:
            """Return the first form matching given id or name in the document."""
            if id_:
                forms = self.html.cssselect(f'form#{id_}')
            elif name:
                forms = self.html.cssselect(f'form[name={name}]')
            else:
                forms = self.forms
            if forms:
                return forms[0]
            return None

        def links(self, selector: str = 'a') -> t.List[HtmlElement]:
            """Get all the links matching the given CSS selector."""
            return self.html.cssselect(selector)

        def link(self, selector: str = 'a') -> t.Optional[HtmlElement]:
            """Get first link matching the given CSS selector."""
            links = self.links(selector)
            if links:
                return links[0]
            return None

        @property
        def metarefresh(self) -> t.Optional[MetaRefreshContent]:
            """Return content of Meta Refresh tag if present."""
            meta_elements = self.html.cssselect('meta[http-equiv="refresh"]')
            if not meta_elements:
                return None
            content = meta_elements[0].attrib.get('content')
            if content is None:
                return None
            match = _meta_refresh_content_re.fullmatch(content)
            if match is None:
                return None
            return MetaRefreshContent(int(match['timeout']), match['url'] or None)

    return ResponseWithForms


@pytest.fixture(scope='session')
def rich_console():
    """Provide a rich console for color output."""
    from rich.console import Console

    return Console()


@pytest.fixture(scope='session')
def colorama() -> t.Iterator[SimpleNamespace]:
    """Provide the colorama print colorizer."""
    from colorama import Back, Fore, Style, deinit, init

    init()
    yield SimpleNamespace(Fore=Fore, Back=Back, Style=Style)
    deinit()


@pytest.fixture(scope='session')
def colorize_code(rich_console) -> t.Callable[[str, t.Optional[str]], str]:
    """Return colorized output for a string of code, for current terminal's colors."""

    def no_colorize(code_string: str, lang: t.Optional[str] = 'python') -> str:
        # Pygments is not available or terminal does not support colour output
        return code_string

    try:
        from pygments import highlight
        from pygments.formatters import (
            Terminal256Formatter,
            TerminalFormatter,
            TerminalTrueColorFormatter,
        )
        from pygments.lexers import get_lexer_by_name, guess_lexer
    except ModuleNotFoundError:
        return no_colorize

    if rich_console.color_system == 'truecolor':
        formatter = TerminalTrueColorFormatter()
    elif rich_console.color_system == '256':
        formatter = Terminal256Formatter()
    elif rich_console.color_system == 'standard':
        formatter = TerminalFormatter()
    else:
        # color_system is `None` or `'windows'` or something unrecognised. No colours.
        return no_colorize

    def colorize(code_string: str, lang: t.Optional[str] = 'python') -> str:
        if lang in (None, 'auto'):
            lexer = guess_lexer(code_string)
        else:
            lexer = get_lexer_by_name(lang)
        return highlight(code_string, lexer, formatter).rstrip()

    return colorize


@pytest.fixture(scope='session')
def print_stack(pytestconfig, colorama, colorize_code) -> t.Callable[[int, int], None]:
    """Print a stack trace up to an outbound call from within this repository."""
    from inspect import stack as inspect_stack
    import os.path

    boundary_path = str(pytestconfig.rootpath)
    if not boundary_path.endswith('/'):
        boundary_path += '/'

    def func(skip: int = 0, indent: int = 2) -> None:
        # Retrieve call stack, removing ourselves and as many frames as the caller wants
        # to skip
        prefix = ' ' * indent
        stack = inspect_stack()[2 + skip :]

        lines = []
        # Reverse list to order from outermost to innermost, and remove outer frames
        # that are outside our code
        stack.reverse()
        while stack and not stack[0].filename.startswith(boundary_path):
            stack.pop(0)

        # Find the first exit from our code and keep only that line and later to
        # remove unneccesary context
        for index, fi in enumerate(stack):
            if not fi.filename.startswith(boundary_path):
                stack = stack[index - 1 :]
                break

        for fi in stack:
            line_color = (
                colorama.Fore.RED
                if fi.filename.startswith(boundary_path)
                else colorama.Fore.GREEN
            )
            code_line = '\n'.join(fi.code_context or []).strip()
            lines.append(
                f'{prefix}{line_color}'
                f'{os.path.relpath(fi.filename)}:{fi.lineno}::{fi.function}'
                f'\t{colorize_code(code_line)}'
                f'{colorama.Style.RESET_ALL}'
            )
        del stack
        # Now print the lines
        print(*lines, sep='\n')  # noqa: T201

    return func


@pytest.fixture(scope='session')
def app(funnel) -> Flask:
    """App fixture with testing flag set."""
    funnel.app.config['TESTING'] = True
    return funnel.app


@pytest.fixture(scope='session')
def shortlinkapp(funnel) -> Flask:
    """Shortlink app with testing flag set."""
    funnel.shortlinkapp.config['TESTING'] = True
    return funnel.shortlinkapp


@pytest.fixture()
def app_context(app) -> t.Iterator:
    """Create an app context for the test."""
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture()
def request_context(app) -> t.Iterator:
    """Create a request context with default values for the test."""
    with app.test_request_context() as ctx:
        yield ctx


config_test_keys: t.Dict[str, t.Set[str]] = {
    'recaptcha': {'RECAPTCHA_PUBLIC_KEY', 'RECAPTCHA_PRIVATE_KEY'},
    'twilio': {'SMS_TWILIO_SID', 'SMS_TWILIO_TOKEN'},
    'exotel': {'SMS_EXOTEL_SID', 'SMS_EXOTEL_TOKEN'},
    'gmaps': {'GOOGLE_MAPS_API_KEY'},
    'youtube': {'YOUTUBE_API_KEY'},
    'vimeo': {'VIMEO_CLIENT_ID', 'VIMEO_CLIENT_SECRET', 'VIMEO_ACCESS_TOKEN'},
    'oauth-twitter': {'OAUTH_TWITTER_KEY', 'OAUTH_TWITTER_SECRET'},
    'oauth-google': {'OAUTH_GOOGLE_KEY', 'OAUTH_GOOGLE_SECRET'},
    'oauth-github': {'OAUTH_GITHUB_KEY', 'OAUTH_GITHUB_SECRET'},
    'oauth-linkedin': {'OAUTH_LINKEDIN_KEY', 'OAUTH_LINKEDIN_SECRET'},
    'oauth-zoom': {'OAUTH_ZOOM_KEY', 'OAUTH_ZOOM_SECRET'},
    'geoip-data': {'GEOIP_DB_CITY', 'GEOIP_DB_ASN'},
    'telegram-notify': {'TELEGRAM_NOTIFY_APIKEY'},
    'telegram-stats': {'TELEGRAM_STATS_APIKEY', 'TELEGRAM_STATS_CHATID'},
    'telegram-error': {'TELEGRAM_ERROR_APIKEY', 'TELEGRAM_ERROR_CHATID'},
}


@pytest.fixture(autouse=True)
def _requires_config(request) -> None:
    """Skip test if app is missing config (using ``requires_config`` mark)."""
    if request.node.get_closest_marker('requires_config'):
        app = request.getfixturevalue('app')
        for mark in request.node.iter_markers('requires_config'):
            for config in mark.args:
                if config not in config_test_keys:
                    pytest.fail(f"Unknown required config {config}")
                for setting_key in config_test_keys[config]:
                    if not app.config.get(setting_key):
                        pytest.skip(
                            f"Skipped due to missing config for {config} in app.config:"
                            f" {setting_key}"
                        )


@pytest.fixture(scope='session')
def _app_events(colorama, print_stack, app) -> t.Iterator:
    """Fixture to report Flask signals with a stack trace when debugging a test."""
    from functools import partial

    import flask

    def signal_handler(signal_name, *args, **kwargs):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}Signal:{colorama.Style.NORMAL}"
            f" {colorama.Fore.YELLOW}{signal_name}{colorama.Style.RESET_ALL}"
        )
        print_stack(2)  # Skip two stack frames from Blinker

    request_started = partial(signal_handler, 'request_started')
    request_finished = partial(signal_handler, 'request_finished')
    request_tearing_down = partial(signal_handler, 'request_tearing_down')
    appcontext_tearing_down = partial(signal_handler, 'appcontext_tearing_down')
    appcontext_pushed = partial(signal_handler, 'appcontext_pushed')
    appcontext_popped = partial(signal_handler, 'appcontext_popped')

    flask.request_started.connect(request_started, app)
    flask.request_finished.connect(request_finished, app)
    flask.request_tearing_down.connect(request_tearing_down, app)
    flask.appcontext_tearing_down.connect(appcontext_tearing_down, app)
    flask.appcontext_pushed.connect(appcontext_pushed, app)
    flask.appcontext_popped.connect(appcontext_popped, app)

    yield

    flask.request_started.disconnect(request_started, app)
    flask.request_finished.disconnect(request_finished, app)
    flask.request_tearing_down.disconnect(request_tearing_down, app)
    flask.appcontext_tearing_down.disconnect(appcontext_tearing_down, app)
    flask.appcontext_pushed.disconnect(appcontext_pushed, app)
    flask.appcontext_popped.disconnect(appcontext_popped, app)


@pytest.fixture()
def _database_events(models, colorama, colorize_code, print_stack) -> t.Iterator:
    """
    Fixture to report database session events for debugging a test.

    If a test is exhibiting unusual behaviour, add this fixture to trace db events::

        @pytest.mark.usefixtures('_database_events')
        def test_whatever() -> None:
            ...
    """
    from pprint import saferepr

    def safe_repr(entity):
        try:
            return saferepr(entity)
        except Exception:  # noqa: B902  # pylint: disable=broad-except
            if hasattr(entity, '__class__'):
                return f'{entity.__class__.__qualname__}(class-repr-error)'
            if hasattr(entity, '__name__'):
                return f'{entity.__name__}(repr-error)'
            return 'repr-error'

    @sa.event.listens_for(models.db.Model, 'init', propagate=True)
    def event_init(obj, args, kwargs):
        rargs = ', '.join(safe_repr(_a) for _a in args)
        rkwargs = ', '.join(f'{_k}={safe_repr(_v)}' for _k, _v in kwargs.items())
        rparams = f'{rargs, rkwargs}' if rargs else rkwargs
        code = colorize_code(f"{obj.__class__.__qualname__}({rparams})")
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: new:{colorama.Style.NORMAL}" f" {code}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'transient_to_pending')
    def event_transient_to_pending(_session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: transient to pending:{colorama.Style.NORMAL}"
            f" {colorize_code(safe_repr(obj))}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'pending_to_transient')
    def event_pending_to_transient(_session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: pending to transient:{colorama.Style.NORMAL}"
            f" {colorize_code(safe_repr(obj))}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'pending_to_persistent')
    def event_pending_to_persistent(_session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: pending to persistent:{colorama.Style.NORMAL}"
            f" {colorize_code(safe_repr(obj))}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'loaded_as_persistent')
    def event_loaded_as_persistent(_session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: loaded as persistent:{colorama.Style.NORMAL}"
            f" {safe_repr(obj)}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'persistent_to_transient')
    def event_persistent_to_transient(_session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: persistent to transient:"
            f"{colorama.Style.NORMAL} {safe_repr(obj)}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'persistent_to_deleted')
    def event_persistent_to_deleted(_session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: persistent to deleted:{colorama.Style.NORMAL}"
            f" {safe_repr(obj)}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'deleted_to_detached')
    def event_deleted_to_detached(_session, obj):
        i = sa.inspect(obj)
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: deleted to detached:{colorama.Style.NORMAL}"
            f" {obj.__class__.__qualname__}/{i.identity}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'persistent_to_detached')
    def event_persistent_to_detached(_session, obj):
        i = sa.inspect(obj)
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: persistent to detached:"
            f"{colorama.Style.NORMAL} {obj.__class__.__qualname__}/{i.identity}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'detached_to_persistent')
    def event_detached_to_persistent(_session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: detached to persistent:"
            f"{colorama.Style.NORMAL} {safe_repr(obj)}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'deleted_to_persistent')
    def event_deleted_to_persistent(session, obj):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}obj: deleted to persistent:{colorama.Style.NORMAL}"
            f" {safe_repr(obj)}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'do_orm_execute')
    def event_do_orm_execute(orm_execute_state):
        state_is = []
        if orm_execute_state.is_column_load:
            state_is.append("is_column_load")
        if orm_execute_state.is_delete:
            state_is.append("is_delete")
        if orm_execute_state.is_insert:
            state_is.append("is_insert")
        if orm_execute_state.is_orm_statement:
            state_is.append("is_orm_statement")
        if orm_execute_state.is_relationship_load:
            state_is.append("is_relationship_load")
        if orm_execute_state.is_select:
            state_is.append("is_select")
        if orm_execute_state.is_update:
            state_is.append("is_update")
        class_name = (
            orm_execute_state.bind_mapper.class_.__qualname__
            if orm_execute_state.bind_mapper
            else None
        )
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}exec:{colorama.Style.NORMAL} {class_name}:"
            f" {', '.join(state_is)}"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'after_begin')
    def event_after_begin(_session, transaction, _connection):
        if transaction.nested:
            if transaction.parent.nested:
                print(  # noqa: T201
                    f"{colorama.Style.BRIGHT}session:{colorama.Style.NORMAL}"
                    f" BEGIN (double nested)"
                )
            else:
                print(  # noqa: T201
                    f"{colorama.Style.BRIGHT}session:{colorama.Style.NORMAL}"
                    f" BEGIN (nested)"
                )
        else:
            print(  # noqa: T201
                f"{colorama.Style.BRIGHT}session:{colorama.Style.NORMAL} BEGIN (outer)"
            )
        print_stack()

    @sa.event.listens_for(DatabaseSessionClass, 'after_commit')
    def event_after_commit(session):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}session:{colorama.Style.NORMAL} COMMIT"
            f" ({session.info!r})"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'after_flush')
    def event_after_flush(session, _flush_context):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}session:{colorama.Style.NORMAL} FLUSH"
            f" ({session.info})"
        )

    @sa.event.listens_for(DatabaseSessionClass, 'after_rollback')
    def event_after_rollback(session):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}session:{colorama.Style.NORMAL} ROLLBACK"
            f" ({session.info})"
        )
        print_stack()

    @sa.event.listens_for(DatabaseSessionClass, 'after_soft_rollback')
    def event_after_soft_rollback(session, _previous_transaction):
        print(  # noqa: T201
            f"{colorama.Style.BRIGHT}session:{colorama.Style.NORMAL} SOFT ROLLBACK"
            f" ({session.info})"
        )
        print_stack()

    @sa.event.listens_for(DatabaseSessionClass, 'after_transaction_create')
    def event_after_transaction_create(_session, transaction):
        if transaction.nested:
            if transaction.parent.nested:
                print(  # noqa: T201
                    f"{colorama.Style.BRIGHT}transaction:{colorama.Style.NORMAL}"
                    f" CREATE (savepoint)"
                )
            else:
                print(  # noqa: T201
                    f"{colorama.Style.BRIGHT}transaction:{colorama.Style.NORMAL}"
                    f" CREATE (fixture)"
                )
        else:
            print(  # noqa: T201
                f"{colorama.Style.BRIGHT}transaction:{colorama.Style.NORMAL}"
                f" CREATE (db)"
            )
        print_stack()

    @sa.event.listens_for(DatabaseSessionClass, 'after_transaction_end')
    def event_after_transaction_end(_session, transaction):
        if transaction.nested:
            if transaction.parent.nested:
                print(  # noqa: T201
                    f"{colorama.Style.BRIGHT}transaction:{colorama.Style.NORMAL} END"
                    f" (double nested)"
                )
            else:
                print(  # noqa: T201
                    f"{colorama.Style.BRIGHT}transaction:{colorama.Style.NORMAL} END"
                    f" (nested)"
                )
        else:
            print(  # noqa: T201
                f"{colorama.Style.BRIGHT}transaction:{colorama.Style.NORMAL} END"
                f" (outer)"
            )
        print_stack()

    yield

    sa.event.remove(models.db.Model, 'init', event_init)
    sa.event.remove(
        DatabaseSessionClass, 'transient_to_pending', event_transient_to_pending
    )
    sa.event.remove(
        DatabaseSessionClass, 'pending_to_transient', event_pending_to_transient
    )
    sa.event.remove(
        DatabaseSessionClass, 'pending_to_persistent', event_pending_to_persistent
    )
    sa.event.remove(
        DatabaseSessionClass, 'loaded_as_persistent', event_loaded_as_persistent
    )
    sa.event.remove(
        DatabaseSessionClass, 'persistent_to_transient', event_persistent_to_transient
    )
    sa.event.remove(
        DatabaseSessionClass, 'persistent_to_deleted', event_persistent_to_deleted
    )
    sa.event.remove(
        DatabaseSessionClass, 'deleted_to_detached', event_deleted_to_detached
    )
    sa.event.remove(
        DatabaseSessionClass, 'persistent_to_detached', event_persistent_to_detached
    )
    sa.event.remove(
        DatabaseSessionClass, 'detached_to_persistent', event_detached_to_persistent
    )
    sa.event.remove(
        DatabaseSessionClass, 'deleted_to_persistent', event_deleted_to_persistent
    )
    sa.event.remove(DatabaseSessionClass, 'do_orm_execute', event_do_orm_execute)
    sa.event.remove(DatabaseSessionClass, 'after_begin', event_after_begin)
    sa.event.remove(DatabaseSessionClass, 'after_commit', event_after_commit)
    sa.event.remove(DatabaseSessionClass, 'after_flush', event_after_flush)
    sa.event.remove(DatabaseSessionClass, 'after_rollback', event_after_rollback)
    sa.event.remove(
        DatabaseSessionClass, 'after_soft_rollback', event_after_soft_rollback
    )
    sa.event.remove(
        DatabaseSessionClass, 'after_transaction_create', event_after_transaction_create
    )
    sa.event.remove(
        DatabaseSessionClass, 'after_transaction_end', event_after_transaction_end
    )


@pytest.fixture(scope='session')
def database(funnel, models, request, app) -> SQLAlchemy:
    """Provide a database structure."""
    with app.app_context():
        models.db.create_all()
        funnel.redis_store.flushdb()

    @request.addfinalizer
    def drop_tables():
        with app.app_context():
            models.db.drop_all()

    return models.db


@pytest.fixture()
def db_session_truncate(
    funnel, app, database, app_context
) -> t.Iterator[DatabaseSessionClass]:
    """Empty the database after each use of the fixture."""
    yield database.session
    sa.orm.close_all_sessions()

    # Iterate through all database engines and empty their tables
    for engine in database.engines.values():
        with engine.begin() as transaction:
            transaction.execute(
                sa.text(
                    '''
                DO $$
                DECLARE tablenames text;
                BEGIN
                    tablenames := string_agg(
                        quote_ident(schemaname) || '.' || quote_ident(tablename), ', ')
                        FROM pg_tables WHERE schemaname = 'public';
                    EXECUTE 'TRUNCATE TABLE ' || tablenames || ' RESTART IDENTITY';
                END; $$'''
                )
            )

    # Clear Redis db too
    funnel.redis_store.flushdb()


@dataclass
class BindConnectionTransaction:
    engine: sa.engine.Engine
    connection: t.Any
    transaction: t.Any


class BoundSession(FsaSession):
    def __init__(
        self,
        db: SQLAlchemy,
        bindcts: t.Dict[t.Optional[str], BindConnectionTransaction],
        **kwargs: t.Any,
    ) -> None:
        super().__init__(db, **kwargs)
        self.bindcts = bindcts

    def get_bind(
        self,
        mapper: t.Optional[t.Any] = None,
        clause: t.Optional[t.Any] = None,
        bind: t.Optional[t.Union[sa.engine.Engine, sa.engine.Connection]] = None,
        **kwargs: t.Any,
    ) -> t.Union[sa.engine.Engine, sa.engine.Connection]:
        if bind is not None:
            return bind
        if mapper is not None:
            mapper = sa.inspect(mapper)
            table = mapper.local_table
            bind_key = table.metadata.info.get('bind_key')
            return self.bindcts[bind_key].connection
        if isinstance(clause, sa.Table):
            bind_key = table.metadata.info.get('bind_key')
            return self.bindcts[bind_key].connection
        return self.bindcts[None].connection


@pytest.fixture()
def db_session_rollback(
    funnel, app, database, app_context
) -> t.Iterator[DatabaseSessionClass]:
    """Create a nested transaction for the test and rollback after."""
    original_session = database.session

    bindcts: t.Dict[t.Optional[str], BindConnectionTransaction] = {}
    for bind, engine in database.engines.items():
        connection = engine.connect()
        transaction = connection.begin()
        bindcts[bind] = BindConnectionTransaction(engine, connection, transaction)
    database.session = database._make_scoped_session(
        {
            'class_': BoundSession,
            'bindcts': bindcts,
            'join_transaction_mode': 'create_savepoint',
        }
    )
    database.session.info['fixture'] = True

    yield database.session

    database.session.info.pop('fixture', None)
    database.session.close()

    for bct in bindcts.values():
        bct.transaction.rollback()
        bct.connection.close()

    database.session = original_session

    # Clear Redis db too
    funnel.redis_store.flushdb()


db_session_implementations = {
    'rollback': 'db_session_rollback',
    'truncate': 'db_session_truncate',
}


@pytest.fixture()
def db_session(request) -> DatabaseSessionClass:
    """
    Database session fixture.

    This fixture may be overridden in another conftest.py to return one of the two
    available session fixtures:

    * ``db_session_truncate``: Which allows unmediated database access but empties table
      contents after each use
    * ``db_session_rollback``: Which nests the session in a SAVEPOINT and rolls back
      after each use

    The rollback approach is significantly faster, but not compatible with tests that
    span multiple app contexts or require special session behaviour. The ``db_session``
    fixture will default to the rollback approach, but can be told to use truncate
    instead:

    * The ``--dbsession`` command-line option defaults to ``rollback`` but can be set to
      ``truncate``, changing it for the entire pytest session
    * An individual test can be decorated with ``@pytest.mark.dbcommit()``
    * A test module or package can override the ``db_session`` fixture to return one of
      the underlying fixtures, thereby overriding both of the above behaviours
    """
    return request.getfixturevalue(
        db_session_implementations[
            'truncate'
            if request.node.get_closest_marker('dbcommit')
            else request.config.getoption('--dbsession')
        ]
    )


@pytest.fixture()
def client(response_with_forms, app, db_session) -> FlaskClient:
    """Provide a test client that commits the db session before any action."""
    from flask.testing import FlaskClient

    client: FlaskClient = FlaskClient(app, response_with_forms, use_cookies=True)
    client_open = client.open

    def commit_before_open(*args, **kwargs):
        db_session.commit()
        return client_open(*args, **kwargs)

    client.open = commit_before_open  # type: ignore[assignment]
    return client


@pytest.fixture(scope='session')
def browser_patches():  # noqa : PT004
    """Patch webdriver for pytest-splinter."""
    from pytest_splinter.webdriver_patches import patch_webdriver

    # Required due to https://github.com/pytest-dev/pytest-splinter/issues/158
    patch_webdriver()


@pytest.fixture(scope='session')
def splinter_webdriver(request) -> str:
    """
    Return an available webdriver, or requested one from CLI options.

    Skips dependent tests if no webdriver is available, but fails if there was an
    explicit request for a webdriver and it's not found.
    """
    driver_executables = {
        'firefox': 'geckodriver',
        'chrome': 'chromedriver',
        'edge': 'msedgedriver',
    }

    driver = request.config.option.splinter_webdriver
    if driver:
        if driver == 'remote':
            # For remote driver, assume necessary config is in CLI options
            return driver
        if driver not in driver_executables:
            # pytest-splinter already validates the possible strings in pytest options.
            # Our list is narrowed down to allow JS-capable browsers only
            pytest.fail(f"Webdriver '{driver}' does not support JavaScript")
        executable = driver_executables[driver]
        if shutil.which(executable):
            return driver
        pytest.fail(
            f"Requested webdriver '{driver}' needs executable '{executable}' in $PATH"
        )
    for driver, executable in driver_executables.items():
        if shutil.which(executable):
            return driver
    pytest.skip("No webdriver found")
    # For pylint and mypy since they don't know that pytest.fail is NoReturn
    return ''  # type: ignore[unreachable]


@pytest.fixture(scope='session')
def splinter_driver_kwargs(splinter_webdriver) -> dict:
    """Disable certification verification when using Chrome webdriver."""
    from selenium import webdriver

    if splinter_webdriver == 'chrome':
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')

        return {'options': options}
    return {}


@pytest.fixture(scope='package')
def live_server(funnel_devtest, database, app):
    """Run application in a separate process."""
    from werkzeug import run_simple

    # Use HTTPS for live server (set to False if required)
    use_https = True
    scheme = 'https' if use_https else 'http'
    # Use app's port from SERVER_NAME as basis for the port to run the live server on
    port_str = app.config['SERVER_NAME'].partition(':')[-1]
    if not port_str or not port_str.isdigit():
        pytest.fail(
            f"App does not have SERVER_NAME specified as host:port in config:"
            f" {app.config['SERVER_NAME']}"
        )
    port = int(port_str)

    # Patch app config to match this fixture's config (scheme and port change).
    with ExitStack() as config_patch_stack:
        for m_app in funnel_devtest.devtest_app.apps_by_host.values():
            m_host = m_app.config['SERVER_NAME'].split(':', 1)[0]
            config_patch_stack.enter_context(
                patch.dict(
                    m_app.config,
                    {'PREFERRED_URL_SCHEME': scheme, 'SERVER_NAME': f'{m_host}:{port}'},
                )
            )

        # Start background worker and yield as fixture
        with funnel_devtest.BackgroundWorker(
            run_simple,
            args=('127.0.0.1', port, funnel_devtest.devtest_app),
            kwargs={
                'use_reloader': False,
                'use_debugger': True,
                'use_evalex': False,
                'threaded': True,
                'ssl_context': 'adhoc' if use_https else None,
            },
            probe_at=('127.0.0.1', port),
            mock_transports=True,
        ) as server:
            yield SimpleNamespace(
                background_worker=server,
                transport_calls=server.calls,
                url=f'{scheme}://{app.config["SERVER_NAME"]}/',
                urls=[
                    f'{scheme}://{m_app.config["SERVER_NAME"]}/'
                    for m_app in funnel_devtest.devtest_app.apps_by_host.values()
                ],
            )


@pytest.fixture()
def csrf_token(client) -> str:
    """Supply a CSRF token for use in form submissions."""
    return client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)


@pytest.fixture()
def login(app, client, db_session) -> SimpleNamespace:
    """Provide a login fixture."""

    def as_(user) -> None:
        db_session.commit()
        with client.session_transaction() as session:
            # TODO: This depends on obsolete code in views/login_session that replaces
            # cookie session authentication with db-backed authentication. It's long
            # pending removal
            session['userid'] = user.userid
        # Perform a request to convert the session userid into a UserSession
        client.get('/api/1/user/get')

    def logout() -> None:
        # TODO: Test this
        client.delete_cookie(
            client.server_name, 'lastuser', domain=app.config['LASTUSER_COOKIE_DOMAIN']
        )

    return SimpleNamespace(as_=as_, logout=logout)


# --- Sample data: users, organizations, projects, etc ---------------------------------

# These names are adapted from the Discworld universe. Backstories can be found at:
# * https://discworld.fandom.com/
# * https://wiki.lspace.org/


# --- Users


@pytest.fixture()
def user_twoflower(models, db_session) -> funnel_models.User:
    """
    Twoflower is a tourist from the Agatean Empire who goes on adventures.

    As a tourist unfamiliar with local customs, Twoflower represents our naive user,
    having only made a user account but not having picked a username or made any other
    affiliations.
    """
    user = models.User(fullname="Twoflower")
    db_session.add(user)
    return user


@pytest.fixture()
def user_rincewind(models, db_session) -> funnel_models.User:
    """
    Rincewind is a wizard and a former member of Unseen University.

    Rincewind is Twoflower's guide in the first two books, and represents our fully
    initiated user in tests.
    """
    user = models.User(username='rincewind', fullname="Rincewind")
    db_session.add(user)
    return user


@pytest.fixture()
def user_death(models, db_session) -> funnel_models.User:
    """
    Death is the epoch user, present at the beginning and always having the last word.

    Since Death predates all other users in tests, any call to `merge_users` or
    `migrate_user` always transfers assets to Death. The fixture has created_at set to
    the epoch to represent this. Death is also a site admin.
    """
    user = models.User(
        username='death',
        fullname="Death",
        created_at=datetime(1970, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(user)
    return user


@pytest.fixture()
def user_mort(models, db_session) -> funnel_models.User:
    """
    Mort is Death's apprentice, and a site admin in tests.

    Mort has a created_at in the past (the publication date of the book), granting
    priority when merging user accounts. Unlike Death, Mort does not have a username or
    profile, so Mort will acquire it from a merged user.
    """
    user = models.User(
        fullname="Mort", created_at=datetime(1987, 11, 12, tzinfo=timezone.utc)
    )
    db_session.add(user)
    return user


@pytest.fixture()
def user_susan(models, db_session) -> funnel_models.User:
    """
    Susan Sto Helit (also written Sto-Helit) is Death's grand daughter.

    Susan inherits Death's role as a site admin and plays a correspondent with Mort.
    """
    user = models.User(username='susan', fullname="Susan Sto Helit")
    db_session.add(user)
    return user


@pytest.fixture()
def user_lutze(models, db_session) -> funnel_models.User:
    """
    Lu-Tze is a history monk and sweeper at the Monastery of Oi-Dong.

    Lu-Tze plays the role of a site editor, cleaning up after messy users.
    """
    user = models.User(username='lu-tze', fullname="Lu-Tze")
    db_session.add(user)
    return user


@pytest.fixture()
def user_ridcully(models, db_session) -> funnel_models.User:
    """
    Mustrum Ridcully, archchancellor of Unseen University.

    Ridcully serves as an owner of the Unseen University organization in tests.
    """
    user = models.User(username='ridcully', fullname="Mustrum Ridcully")
    db_session.add(user)
    return user


@pytest.fixture()
def user_librarian(models, db_session) -> funnel_models.User:
    """
    Librarian of Unseen University, currently an orangutan.

    The Librarian serves as an admin of the Unseen University organization in tests.
    """
    user = models.User(username='librarian', fullname="The Librarian")
    db_session.add(user)
    return user


@pytest.fixture()
def user_ponder_stibbons(models, db_session) -> funnel_models.User:
    """
    Ponder Stibbons, maintainer of Hex, the computer powered by an Anthill Inside.

    Admin of UU org.
    """
    user = models.User(username='ponder-stibbons', fullname="Ponder Stibbons")
    db_session.add(user)
    return user


@pytest.fixture()
def user_vetinari(models, db_session) -> funnel_models.User:
    """
    Havelock Vetinari, patrician (aka dictator) of Ankh-Morpork.

    Co-owner of the City Watch organization in our tests.
    """
    user = models.User(username='vetinari', fullname="Havelock Vetinari")
    db_session.add(user)
    return user


@pytest.fixture()
def user_vimes(models, db_session) -> funnel_models.User:
    """
    Samuel Vimes, commander of the Ankh-Morpork City Watch.

    Co-owner of the City Watch organization in our tests.
    """
    user = models.User(username='vimes', fullname="Sam Vimes")
    db_session.add(user)
    return user


@pytest.fixture()
def user_carrot(models, db_session) -> funnel_models.User:
    """
    Carrot Ironfoundersson, captain of the Ankh-Morpork City Watch.

    Admin of the organization in our tests.
    """
    user = models.User(username='carrot', fullname="Carrot Ironfoundersson")
    db_session.add(user)
    return user


@pytest.fixture()
def user_angua(models, db_session) -> funnel_models.User:
    """
    Delphine Angua von Überwald, member of the Ankh-Morpork City Watch, and foreigner.

    Represents a user who (a) gets promoted in her organization, and (b) prefers an
    foreign, unsupported language.
    """
    # We assign here the locale for Interlingue ('ie'), a constructed language, on the
    # assumption that it will never be supported. "Uberwald" is the German translation
    # of Transylvania, which is located in Romania. Interlingue is the work of an
    # Eastern European, and has since been supplanted by Interlingua, with ISO 639-1
    # code 'ia'. It is therefore reasonably safe to assume Interlingue is dead.
    user = models.User(fullname="Angua von Überwald", locale='ie', auto_locale=False)
    db_session.add(user)
    return user


@pytest.fixture()
def user_dibbler(models, db_session) -> funnel_models.User:
    """
    Cut Me Own Throat (or C.M.O.T) Dibbler, huckster who exploits small opportunities.

    Represents the spammer in our tests, from spam comments to spam projects.
    """
    user = models.User(username='dibbler', fullname="CMOT Dibbler")
    db_session.add(user)
    return user


@pytest.fixture()
def user_wolfgang(models, db_session) -> funnel_models.User:
    """
    Wolfgang von Überwald, brother of Angua, violent shapeshifter.

    Represents an attacker who changes appearance by changing identifiers or making
    sockpuppet user accounts.
    """
    user = models.User(username='wolfgang', fullname="Wolfgang von Überwald")
    db_session.add(user)
    return user


@pytest.fixture()
def user_om(models, db_session) -> funnel_models.User:
    """
    Great God Om of the theocracy of Omnia, who has lost his believers.

    Moves between having a user account and an org account in tests, creating a new user
    account for Brutha, the last believer.
    """
    user = models.User(username='omnia', fullname="Om")
    db_session.add(user)
    return user


# --- Organizations


@pytest.fixture()
def org_ankhmorpork(models, db_session, user_vetinari) -> funnel_models.Organization:
    """
    City of Ankh-Morpork, here representing the government rather than location.

    Havelock Vetinari is the Patrician (aka dictator), and sponsors various projects to
    develop the city.
    """
    org = models.Organization(
        name='ankh-morpork', title="Ankh-Morpork", owner=user_vetinari
    )
    db_session.add(org)
    return org


@pytest.fixture()
def org_uu(
    models, db_session, user_ridcully, user_librarian, user_ponder_stibbons
) -> funnel_models.Organization:
    """
    Unseen University is located in Ankh-Morpork.

    Staff:

    * Alberto Malich, founder emeritus (not listed here since no corresponding role)
    * Mustrum Ridcully, archchancellor (owner)
    * The Librarian, head of the library (admin)
    * Ponder Stibbons, Head of Inadvisably Applied Magic (admin)
    """
    org = models.Organization(name='UU', title="Unseen University", owner=user_ridcully)
    db_session.add(org)
    db_session.add(
        models.OrganizationMembership(
            organization=org,
            user=user_librarian,
            is_owner=False,
            granted_by=user_ridcully,
        )
    )
    db_session.add(
        models.OrganizationMembership(
            organization=org,
            user=user_ponder_stibbons,
            is_owner=False,
            granted_by=user_ridcully,
        )
    )
    return org


@pytest.fixture()
def org_citywatch(
    models, db_session, user_vetinari, user_vimes, user_carrot
) -> funnel_models.Organization:
    """
    City Watch of Ankh-Morpork (a sub-organization).

    Staff:

    * Havelock Vetinari, Patrician of the city, legal owner but with no operating role
    * Sam Vimes, commander (owner)
    * Carrot Ironfoundersson, captain (admin)
    * Angua von Uberwald, corporal (unlisted, as there is no member role)
    """
    org = models.Organization(
        name='city-watch', title="City Watch", owner=user_vetinari
    )
    db_session.add(org)
    db_session.add(
        models.OrganizationMembership(
            organization=org, user=user_vimes, is_owner=True, granted_by=user_vetinari
        )
    )
    db_session.add(
        models.OrganizationMembership(
            organization=org, user=user_carrot, is_owner=False, granted_by=user_vimes
        )
    )
    return org


# --- Projects
# Fixtures from this point on drift away from Discworld, to reflect the unique contours
# of the product being tested. Maintaining fidelity to Discworld is hard.


@pytest.fixture()
def project_expo2010(
    models, db_session, org_ankhmorpork, user_vetinari
) -> funnel_models.Project:
    """Ankh-Morpork hosts its 2010 expo."""
    db_session.flush()

    project = models.Project(
        profile=org_ankhmorpork.profile,
        user=user_vetinari,
        title="Ankh-Morpork 2010",
        tagline="Welcome to Ankh-Morpork, tourists!",
        description="The city doesn't have tourists. Let's change that.",
    )
    db_session.add(project)
    return project


@pytest.fixture()
def project_expo2011(
    models, db_session, org_ankhmorpork, user_vetinari
) -> funnel_models.Project:
    """Ankh-Morpork hosts its 2011 expo."""
    db_session.flush()

    project = models.Project(
        profile=org_ankhmorpork.profile,
        user=user_vetinari,
        title="Ankh-Morpork 2011",
        tagline="Welcome back, our pub's changed",
        description="The Broken Drum is gone, but we have The Mended Drum now.",
    )
    db_session.add(project)
    return project


@pytest.fixture()
def project_ai1(
    models, db_session, org_uu, user_ponder_stibbons
) -> funnel_models.Project:
    """
    Anthill Inside conference, hosted by Unseen University (an inspired event).

    Based on Soul Music, which features the first appearance of Hex, published 1994.
    """
    db_session.flush()

    project = models.Project(
        profile=org_uu.profile,
        user=user_ponder_stibbons,
        title="Soul Music",
        tagline="Hex makes an initial appearance",
        description="Hex has its origins in a device that briefly appeared in Soul"
        " Music, created by Ponder Stibbons and some student Wizards in the High Energy"
        " Magic building. In this form it was simply a complex network of glass tubes,"
        " containing ants. The wizards could then use punch cards to control which"
        " tubes the ants could crawl through, enabling it to perform simple"
        " mathematical functions.",
    )
    db_session.add(project)
    return project


@pytest.fixture()
def project_ai2(
    models, db_session, org_uu, user_ponder_stibbons
) -> funnel_models.Project:
    """
    Anthill Inside conference, hosted by Unseen University (an inspired event).

    Based on Interesting Times.
    """
    db_session.flush()

    project = models.Project(
        profile=org_uu.profile,
        user=user_ponder_stibbons,
        title="Interesting Times",
        tagline="Hex invents parts for itself",
        description="Hex has become a lot more complex, and is constantly reinventing"
        " itself, meaning several new components of it are mysteries to those at UU.",
    )
    db_session.add(project)
    return project


# --- Client apps


@pytest.fixture()
def client_hex(models, db_session, org_uu) -> funnel_models.Project:
    """
    Hex, supercomputer at Unseen University, powered by an Anthill Inside.

    Owned by UU (owner) and administered by Ponder Stibbons (no corresponding role).
    """
    # TODO: AuthClient needs to move to account (nee profile) as the parent model
    auth_client = models.AuthClient(
        title="Hex",
        organization=org_uu,
        confidential=True,
        website='https://example.org/',
        redirect_uris=['https://example.org/callback'],
    )
    db_session.add(auth_client)
    return auth_client


@pytest.fixture()
def client_hex_credential(models, db_session, client_hex) -> SimpleNamespace:
    cred, secret = models.AuthClientCredential.new(client_hex)
    db_session.add(cred)
    return SimpleNamespace(cred=cred, secret=secret)


@pytest.fixture()
def all_fixtures(  # pylint: disable=too-many-arguments,too-many-locals
    db_session,
    user_twoflower,
    user_rincewind,
    user_death,
    user_mort,
    user_susan,
    user_lutze,
    user_ridcully,
    user_librarian,
    user_ponder_stibbons,
    user_vetinari,
    user_vimes,
    user_carrot,
    user_angua,
    user_dibbler,
    user_wolfgang,
    user_om,
    org_ankhmorpork,
    org_uu,
    org_citywatch,
    project_expo2010,
    project_expo2011,
    project_ai1,
    project_ai2,
    client_hex,
) -> SimpleNamespace:
    """Return All Discworld fixtures at once."""
    db_session.commit()
    return SimpleNamespace(**locals())


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# --- Old fixtures, to be removed when tests are updated -------------------------------


TEST_DATA = {
    'users': {
        'testuser': {
            'name': "testuser",
            'fullname': "Test User",
        },
        'testuser2': {
            'name': "testuser2",
            'fullname': "Test User 2",
        },
        'test-org-owner': {
            'name': "test-org-owner",
            'fullname': "Test User 2",
        },
        'test-org-admin': {
            'name': "test-org-admin",
            'fullname': "Test User 3",
        },
    }
}


@pytest.fixture()
def new_user(models, db_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['testuser'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_user2(models, db_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['testuser2'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_user_owner(models, db_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['test-org-owner'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_user_admin(models, db_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['test-org-admin'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_organization(
    models, db_session, new_user_owner, new_user_admin
) -> funnel_models.Organization:
    org = models.Organization(owner=new_user_owner, title="Test org", name='test-org')
    db_session.add(org)

    admin_membership = models.OrganizationMembership(
        organization=org, user=new_user_admin, is_owner=False, granted_by=new_user_owner
    )
    db_session.add(admin_membership)
    db_session.commit()
    return org


@pytest.fixture()
def new_team(models, db_session, new_user, new_organization) -> funnel_models.Team:
    team = models.Team(title="Owners", organization=new_organization)
    db_session.add(team)
    team.users.append(new_user)
    db_session.commit()
    return team


@pytest.fixture()
def new_project(
    models, db_session, new_organization, new_user
) -> funnel_models.Project:
    project = models.Project(
        profile=new_organization.profile,
        user=new_user,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture()
def new_project2(
    models, db_session, new_organization, new_user_owner
) -> funnel_models.Project:
    project = models.Project(
        profile=new_organization.profile,
        user=new_user_owner,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture()
def new_main_label(models, db_session, new_project) -> funnel_models.Label:
    main_label_a = models.Label(
        title="Parent Label A", project=new_project, description="A test parent label"
    )
    new_project.all_labels.append(main_label_a)
    label_a1 = models.Label(title="Label A1", icon_emoji="👍", project=new_project)
    label_a2 = models.Label(title="Label A2", project=new_project)

    main_label_a.options.append(label_a1)
    main_label_a.options.append(label_a2)
    main_label_a.required = True
    main_label_a.restricted = True
    db_session.commit()

    return main_label_a


@pytest.fixture()
def new_main_label_unrestricted(models, db_session, new_project) -> funnel_models.Label:
    main_label_b = models.Label(
        title="Parent Label B", project=new_project, description="A test parent label"
    )
    new_project.all_labels.append(main_label_b)
    label_b1 = models.Label(title="Label B1", icon_emoji="👍", project=new_project)
    label_b2 = models.Label(title="Label B2", project=new_project)

    main_label_b.options.append(label_b1)
    main_label_b.options.append(label_b2)
    main_label_b.required = False
    main_label_b.restricted = False
    db_session.commit()

    return main_label_b


@pytest.fixture()
def new_label(models, db_session, new_project) -> funnel_models.Label:
    label_b = models.Label(title="Label B", icon_emoji="🔟", project=new_project)
    new_project.all_labels.append(label_b)
    db_session.add(label_b)
    db_session.commit()
    return label_b


@pytest.fixture()
def new_proposal(models, db_session, new_user, new_project) -> funnel_models.Proposal:
    proposal = models.Proposal(
        user=new_user,
        project=new_project,
        title="Test Proposal",
        body="Test proposal description",
    )
    db_session.add(proposal)
    db_session.commit()
    return proposal


@pytest.fixture()
def fail_with_diff():
    def func(left, right):
        if left != right:
            difference = unified_diff(left.split('\n'), right.split('\n'))
            msg = []
            for line in difference:
                if not line.startswith(' '):
                    msg.append(line)
            pytest.fail('\n'.join(msg), pytrace=False)

    return func
