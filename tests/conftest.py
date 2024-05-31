"""Test configuration and fixtures."""

# pylint: disable=import-outside-toplevel,redefined-outer-name

from __future__ import annotations

import os.path
import re
import time
import warnings
from collections.abc import Callable, Generator
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import unified_diff
from dis import disassemble
from functools import partial
from inspect import stack as inspect_stack
from io import StringIO
from pprint import saferepr
from textwrap import indent
from types import MethodType, ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol, Self, cast, get_type_hints
from unittest.mock import patch

import flask
import pytest
import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
import sqlalchemy.orm as sa_orm
import typeguard
from flask import Flask, session
from flask.ctx import AppContext, RequestContext
from flask.testing import FlaskClient
from flask.wrappers import Response
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.session import Session as FsaSession
from flask_wtf.csrf import generate_csrf
from lxml.html import FormElement, HtmlElement, fromstring
from rich.console import Console
from rich.highlighter import RegexHighlighter, ReprHighlighter
from rich.markup import escape as rich_escape
from rich.syntax import Syntax
from rich.text import Text
from sqlalchemy import event
from sqlalchemy.orm import Session as DatabaseSessionClass, scoped_session
from werkzeug import run_simple

if TYPE_CHECKING:
    import funnel.models as funnel_models
    from funnel.devtest import BackgroundWorker, CapturedCalls

# MARK: Pytest config ------------------------------------------------------------------

MAX_DEADLOCK_RETRIES = 3


def pytest_addoption(parser: pytest.Parser) -> None:
    """Allow db_session to be configured in the command line."""
    parser.addoption(
        '--dbsession',
        action='store',
        default='rollback',
        choices=('rollback', 'truncate'),
        help=(
            "Use db_session with 'rollback' (default) or 'truncate' (slower but more"
            " production-like)"
        ),
    )


def pytest_collection_modifyitems(items: list[pytest.Function]) -> None:
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
        'tests/e2e/basic',
        'tests/e2e/account_user',
        'tests/e2e/account',
        'tests/e2e/project',
        'tests/e2e',
        'tests/features',
    )

    def sort_key(item: pytest.Function) -> tuple[int, str]:
        # pytest.Function's base class pytest.Item reports the file containing the test
        # as item.location == (file_path, line_no, function_name). However, pytest-bdd
        # reports itself for file_path, so we can't use that and must extract the path
        # from the test module instead
        module_file = item.module.__file__ if item.module is not None else ''
        for counter, path in enumerate(test_order):
            if path in module_file:
                return counter, module_file
        return -1, module_file

    items.sort(key=sort_key)


# Adapted from https://github.com/untitaker/pytest-fixture-typecheck
def pytest_runtest_call(item: pytest.Function) -> None:
    try:
        annotations = get_type_hints(
            item.obj,
            globalns=item.obj.__globals__,
            localns={'Any': Any},  # pytest-bdd appears to insert an `Any` annotation
        )
    except TypeError:
        # get_type_hints may fail on Python <3.10 because pytest-bdd appears to have
        # `dict[str, str]` as a type somewhere, and builtin type subscripting isn't
        # supported yet
        warnings.warn(  # noqa: B028
            f"Type annotations could not be retrieved for {item.obj.__qualname__}",
            RuntimeWarning,
        )
        return
    except NameError as exc:
        pytest.fail(
            f"{item.obj.__qualname__} has an unknown annotation for {exc.name}."
            " Is it imported within a TYPE_CHECKING test?"
        )

    for attr, type_ in annotations.items():
        if attr in item.funcargs and not getattr(type_, '_is_protocol', False):
            typeguard.check_type(item.funcargs[attr], type_)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Add line numbers to log report, for easier discovery in code editors."""
    # Report location of test (failing line number if available, else test location)
    filename, line_no, domain = report.location
    if (
        report.longrepr is not None
        and (repr_traceback := getattr(report.longrepr, 'reprtraceback', None))
        is not None
        and (repr_file_loc := repr_traceback.reprentries[0].reprfileloc).path
        == filename
    ):
        line_no = repr_file_loc.lineno
    if report.nodeid.startswith(filename):
        # Only insert a line number if the existing `nodeid`` refers to the same
        # filename. Needed for pytest-bdd, which constructs tests and refers the
        # filename that imported the scenario. This file will not have the actual test
        # function, so no line number reference is possible; the `filename` in the
        # report will refer to pytest-bdd internals
        report.nodeid = f'{filename}:{line_no}::{domain}'


# MARK: Playwright browser config ------------------------------------------------------


@pytest.fixture(scope='session')
def browser_context_args(browser_context_args: dict) -> dict:
    """The test server uses HTTPS with a self-signed certificate, so no verify."""
    return browser_context_args | {'ignore_https_errors': True}


# MARK: Import fixtures ----------------------------------------------------------------


@pytest.fixture(scope='session')
def funnel() -> ModuleType:
    """Funnel package."""
    return pytest.importorskip('funnel')


@pytest.fixture(scope='session')
def models() -> ModuleType:
    """Funnel models package."""
    return pytest.importorskip('funnel.models')


@pytest.fixture(scope='session')
def forms() -> ModuleType:
    """Funnel forms package."""
    return pytest.importorskip('funnel.forms')


@pytest.fixture(scope='session')
def views() -> ModuleType:
    """Funnel views package."""
    return pytest.importorskip('funnel.views')


@pytest.fixture(scope='session')
def funnel_devtest() -> ModuleType:
    """Return devtest module as a fixture."""
    return pytest.importorskip('funnel.devtest')


# MARK: Fixtures -----------------------------------------------------------------------


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


class MetaRefreshContent(NamedTuple):
    """Timeout and optional URL in a Meta Refresh tag."""

    timeout: int
    url: str | None = None


class TestResponse(Response):
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

    # Tell Pytest this class isn't a test
    __test__ = False

    if TYPE_CHECKING:
        #: Type hint for the `text` cached_property available via
        #: :class:`werkzeug.test.TestResponse`, which will be used to make a subclass
        #: of this class in :class:`werkzeug.test.Client`
        @property
        def text(self) -> str: ...

    _parsed_html: HtmlElement | None = None

    @property
    def html(self) -> HtmlElement:
        """Return the parsed HTML tree."""
        if self._parsed_html is None:
            self._parsed_html = fromstring(self.data)

            # add click method to all links
            def _click(
                self: HtmlElement, client: TestClient, **kwargs: Any
            ) -> TestResponse:
                # `self` is the `a` element here
                path = self.attrib['href']
                return client.get(path, **kwargs)

            for link in self._parsed_html.iter('a'):
                link.click = MethodType(_click, link)  # type: ignore[attr-defined]

            # add submit method to all forms
            def _submit(
                self: FormElement,
                client: TestClient,
                path: str | None = None,
                **kwargs: Any,
            ) -> TestResponse:
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

            for form in self._parsed_html.forms:
                form.submit = MethodType(_submit, form)  # type: ignore[attr-defined]
        return self._parsed_html

    @property
    def forms(self) -> list[FormElement]:
        """
        Return list of all forms in the document.

        Contains the LXML form type as documented at
        http://lxml.de/lxmlhtml.html#forms with an additional `.submit(client)`
        method to submit the form.
        """
        return self.html.forms

    def form(
        self, id_: str | None = None, name: str | None = None
    ) -> FormElement | None:
        """Return the first form matching given id or name in the document."""
        if id_:
            forms = cast(list[FormElement], self.html.cssselect(f'form#{id_}'))
        elif name:
            forms = cast(list[FormElement], self.html.cssselect(f'form[name={name}]'))
        else:
            forms = self.forms
        if forms:
            return forms[0]
        return None

    def links(self, selector: str = 'a') -> list[HtmlElement]:
        """Get all the links matching the given CSS selector."""
        return self.html.cssselect(selector)

    def link(self, selector: str = 'a') -> HtmlElement | None:
        """Get first link matching the given CSS selector."""
        links = self.links(selector)
        if links:
            return links[0]
        return None

    @property
    def metarefresh(self) -> MetaRefreshContent | None:
        """Get content of Meta Refresh tag if present."""
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


@pytest.fixture(scope='session')
def rich_console() -> Console:
    """Provide a rich console for colour output."""
    return Console(highlight=False)


class PrintStackProtocol(Protocol):
    def __call__(self, skip: int = 0, limit: int | None = None) -> None: ...


@pytest.fixture(scope='session')
def print_stack(
    pytestconfig: pytest.Config, rich_console: Console
) -> PrintStackProtocol:
    """Print a stack trace up to an outbound call from within this repository."""
    boundary_path = str(pytestconfig.rootpath)
    if not boundary_path.endswith('/'):
        boundary_path += '/'

    class PathHighlighter(RegexHighlighter):
        highlights = [
            r'^(?=(?:\.\./|\.venv/))(?P<blue>.*)',
            r'^(?!(?:\.\./|\.venv/))(?P<green>.*)',
            r'(?P<dim>.*/)(?P<bold>.+)',
        ]

    def func(skip: int = 0, limit: int | None = None) -> None:
        # Retrieve call stack, removing ourselves and as many frames as the caller wants
        # to skip
        stack = inspect_stack()[2 + skip :]
        try:
            path_highlighter = PathHighlighter()
            lines: list[Text | Syntax] = []
            # Reverse list to order from outermost to innermost, and remove outer frames
            # that are outside our code
            stack.reverse()
            while stack and (
                stack[0].filename.startswith(boundary_path + '.venv/')
                or not stack[0].filename.startswith(boundary_path)
            ):
                stack.pop(0)

            # Find the first exit from our code and keep only that line and later to
            # remove unnecessary context. "Our code" = anything that is within
            # boundary_path but not in a top-level `.venv` folder
            for index, frame_info in enumerate(stack):
                if stack[0].filename.startswith(
                    boundary_path + '.venv/'
                ) or not frame_info.filename.startswith(boundary_path):
                    stack = stack[index - 1 :]
                    break

            for frame_info in stack[:limit]:
                text = Text.assemble(
                    path_highlighter(
                        Text(
                            os.path.relpath(frame_info.filename, boundary_path),
                            style='pygments.string',
                        )
                    ),
                    (':', 'pygments.text'),
                    (str(frame_info.lineno), 'pygments.number'),
                    (' in ', 'dim'),
                    (frame_info.function, 'pygments.function'),
                    ('\t', 'pygments.text'),
                    style='pygments.text',
                )
                lines.append(text)
                if frame_info.code_context:
                    lines.append(
                        Syntax(
                            '\n'.join(
                                [
                                    '    ' + line.strip()
                                    for line in frame_info.code_context
                                ]
                            ),
                            'python',
                            background_color='default',
                            word_wrap=True,
                        )
                    )
                else:
                    dis_file = StringIO()
                    disassemble(
                        frame_info.frame.f_code,
                        lasti=frame_info.frame.f_lasti,
                        file=dis_file,
                    )
                    lines.append(
                        Syntax(
                            indent(dis_file.getvalue().rstrip(), '    '),
                            'python',  # Code is Python bytecode, but this seems to work
                            background_color='default',
                            word_wrap=True,
                        )
                    )

            if limit and limit < len(stack):
                lines.append(Text.assemble((f'✂️ {len(stack)-limit} more…', 'dim')))
        finally:
            del stack
        # Now print the lines
        rich_console.print(*lines)

    return func


@pytest.fixture(scope='session')
def app(funnel) -> Flask:
    """App fixture with testing flag set."""
    assert funnel.app.config['TESTING']
    return funnel.app


@pytest.fixture(scope='session')
def shortlinkapp(funnel) -> Flask:
    """Shortlink app with testing flag set."""
    assert funnel.shortlinkapp.config['TESTING']
    return funnel.shortlinkapp


@pytest.fixture(scope='session')
def unsubscribeapp(funnel) -> Flask:
    """Unsubscribe URL app with testing flag set."""
    assert funnel.unsubscribeapp.config['TESTING']
    return funnel.unsubscribeapp


@pytest.fixture
def app_context(app: Flask) -> Generator[AppContext, None, None]:
    """Create an app context for the test."""
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture
def request_context(app: Flask) -> Generator[RequestContext, None, None]:
    """Create a request context with default values for the test."""
    with app.test_request_context() as ctx:
        yield ctx


config_test_keys: dict[str, set[str]] = {
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
    'support-apikey': {'INTERNAL_SUPPORT_API_KEY'},
}


_mock_config_syntax = (
    "Syntax: @pytest.mark.mock_config('app', {'KEY': value_or_callable},"
    " KEY=value_or_callable)"
)


@pytest.fixture(autouse=True)
def _mock_config(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Mock app config (using ``mock_config`` mark)."""

    def backup_and_apply_config(
        app_name: str, app_fixture: Flask, saved_config: dict, key: str, value: Any
    ) -> None:
        if key in saved_config:
            pytest.fail(f"Duplicate mock for {app_name}.config[{key!r}]")
        if key in app_fixture.config:  # noqa: SIM401
            saved_config[key] = app_fixture.config[key]
        else:
            saved_config[key] = ...  # Sentinel value
        if callable(value):
            value = value()
        if value is ...:
            app_fixture.config.pop(key, None)
        else:
            app_fixture.config[key] = value

    if request.node.get_closest_marker('mock_config'):
        saved_app_config: dict[Flask, Any] = {}
        for mark in request.node.iter_markers('mock_config'):
            if len(mark.args) < 1:
                pytest.fail(_mock_config_syntax)
            app_fixture = request.getfixturevalue(mark.args[0])
            saved_app_config[app_fixture] = {}
            for config in mark.args[1:]:
                if not isinstance(config, dict):
                    pytest.fail(_mock_config_syntax)
                for key, value in config.items():
                    backup_and_apply_config(
                        mark.args[0],
                        app_fixture,
                        saved_app_config[app_fixture],
                        key,
                        value,
                    )
            for key, value in mark.kwargs.items():
                backup_and_apply_config(
                    mark.args[0], app_fixture, saved_app_config[app_fixture], key, value
                )
        yield
        # Restore config after test
        for app_fixture, config in saved_app_config.items():
            for key, value in config.items():
                if value is ...:  # Sentinel value for config to be removed
                    app_fixture.config.pop(key, None)
                else:
                    app_fixture.config[key] = value
    else:
        yield  # 'yield' is required in all code paths in a generator


@pytest.fixture(autouse=True)
def _requires_config(request: pytest.FixtureRequest) -> None:
    """Skip test if app is missing config (using ``requires_config`` mark)."""
    if request.node.get_closest_marker('requires_config'):
        for mark in request.node.iter_markers('requires_config'):
            if len(mark.args) < 2:
                pytest.fail(
                    "Syntax: @pytest.mark.requires_config('app', 'feature', ...)"
                )
            app_fixture = request.getfixturevalue(mark.args[0])
            for config in mark.args[1:]:
                if config not in config_test_keys:
                    pytest.fail(f"Unknown required config {config}")
                for setting_key in config_test_keys[config]:
                    if not app_fixture.config.get(setting_key):
                        pytest.skip(
                            f"Skipped due to missing config for {config} in app.config:"
                            f" {setting_key}"
                        )


@pytest.fixture(scope='session')
def _app_events(
    rich_console: Console, print_stack: PrintStackProtocol, app: Flask
) -> Generator[None, None, None]:
    """Fixture to report Flask signals with a stack trace when debugging a test."""

    def signal_handler(signal_name, *args: Any, **kwargs: Any) -> None:
        rich_console.print(f"[bold]Signal:[/] [yellow]{rich_escape(signal_name)}[/]")
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


@pytest.fixture
def _database_events(
    models: ModuleType, rich_console: Console, print_stack: PrintStackProtocol
) -> Generator[None, None, None]:
    """
    Fixture to report database session events for debugging a test.

    If a test is exhibiting unusual behaviour, add this fixture to trace db events::

        @pytest.mark.usefixtures('_database_events')
        def test_whatever() -> None: ...
    """
    repr_highlighter = ReprHighlighter()

    def safe_repr(entity: Any) -> str:
        try:
            return saferepr(entity)
        except Exception:  # noqa: BLE001  # pylint: disable=broad-except
            if hasattr(entity, '__class__'):
                return f'<ReprError: class {entity.__class__.__qualname__}>'
            if hasattr(entity, '__qualname__'):
                return f'<ReprError: {entity.__qualname__}'
            if hasattr(entity, '__name__'):
                return f'<ReprError: {entity.__name__}'
            return '<ReprError>'

    @event.listens_for(models.Model, 'init', propagate=True)
    def event_init(obj: funnel_models.Model, args, kwargs) -> None:
        rargs = ', '.join(safe_repr(_a) for _a in args)
        rkwargs = ', '.join(f'{_k}={safe_repr(_v)}' for _k, _v in kwargs.items())
        rparams = f'{rargs, rkwargs}' if rargs else rkwargs
        code = f'{obj.__class__.__qualname__}({rparams})'
        rich_console.print(
            Text.assemble(('obj:', 'bold'), ' new: ', repr_highlighter(code))
        )

    @event.listens_for(DatabaseSessionClass, 'transient_to_pending')
    def event_transient_to_pending(_session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' transient → pending: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'pending_to_transient')
    def event_pending_to_transient(_session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' pending → transient: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'pending_to_persistent')
    def event_pending_to_persistent(_session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' pending → persistent: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'loaded_as_persistent')
    def event_loaded_as_persistent(_session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' loaded as persistent: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'persistent_to_transient')
    def event_persistent_to_transient(_session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' persistent → transient: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'persistent_to_deleted')
    def event_persistent_to_deleted(_session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' persistent → deleted: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'deleted_to_detached')
    def event_deleted_to_detached(_session, obj: funnel_models.Model) -> None:
        i = sa.inspect(obj)
        rich_console.print(
            "[bold]obj:[/] deleted → detached:"
            f" {rich_escape(obj.__class__.__qualname__)}/{i.identity}"
        )

    @event.listens_for(DatabaseSessionClass, 'persistent_to_detached')
    def event_persistent_to_detached(_session, obj: funnel_models.Model) -> None:
        i = sa.inspect(obj)
        rich_console.print(
            "[bold]obj:[/] persistent → detached:"
            f" {rich_escape(obj.__class__.__qualname__)}/{i.identity}"
        )

    @event.listens_for(DatabaseSessionClass, 'detached_to_persistent')
    def event_detached_to_persistent(_session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' detached → persistent: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'deleted_to_persistent')
    def event_deleted_to_persistent(session, obj: funnel_models.Model) -> None:
        rich_console.print(
            Text.assemble(
                ('obj:', 'bold'),
                ' deleted → persistent: ',
                repr_highlighter(safe_repr(obj)),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'do_orm_execute')
    def event_do_orm_execute(orm_execute_state: sa_orm.ORMExecuteState) -> None:
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
            else '<unknown>'
        )
        rich_console.print(
            Text.assemble(
                ('exec: ', 'bold'),
                ', '.join(state_is),
                (' on ', 'dim'),
                (class_name, 'repr.call'),
            )
        )

    @event.listens_for(DatabaseSessionClass, 'after_begin')
    def event_after_begin(
        _session, transaction: sa_orm.SessionTransaction, _connection
    ) -> None:
        if transaction.nested:
            if transaction.parent and transaction.parent.nested:
                rich_console.print("[bold]session:[/] BEGIN (double nested)")
            else:
                rich_console.print("[bold]session:[/] BEGIN (nested)")
        else:
            rich_console.print("[bold]session:[/] BEGIN (outer)")
        print_stack(0, 5)

    @event.listens_for(DatabaseSessionClass, 'after_commit')
    def event_after_commit(session: DatabaseSessionClass) -> None:
        rich_console.print(
            Text.assemble(
                ('session:', 'bold'), ' COMMIT ', repr_highlighter(repr(session.info))
            )
        )

    @event.listens_for(DatabaseSessionClass, 'after_flush')
    def event_after_flush(session: DatabaseSessionClass, _flush_context) -> None:
        rich_console.print(
            Text.assemble(
                ('session:', 'bold'), ' FLUSH ', repr_highlighter(repr(session.info))
            )
        )

    @event.listens_for(DatabaseSessionClass, 'after_rollback')
    def event_after_rollback(session: DatabaseSessionClass) -> None:
        rich_console.print(
            Text.assemble(
                ('session:', 'bold'), ' ROLLBACK ', repr_highlighter(repr(session.info))
            )
        )
        print_stack(0, 5)

    @event.listens_for(DatabaseSessionClass, 'after_soft_rollback')
    def event_after_soft_rollback(
        session: DatabaseSessionClass, _previous_transaction
    ) -> None:
        rich_console.print(
            Text.assemble(
                ('session:', 'bold'),
                ' SOFT ROLLBACK ',
                repr_highlighter(repr(session.info)),
            )
        )
        print_stack(0, 5)

    @event.listens_for(DatabaseSessionClass, 'after_transaction_create')
    def event_after_transaction_create(
        _session, transaction: sa_orm.SessionTransaction
    ) -> None:
        if transaction.nested:
            if transaction.parent and transaction.parent.nested:
                rich_console.print("[bold]transaction:[/] CREATE (savepoint)")
            else:
                rich_console.print("[bold]transaction:[/] CREATE (fixture)")
        else:
            rich_console.print("[bold]transaction:[/] CREATE (db)")
        print_stack(0, 5)

    @event.listens_for(DatabaseSessionClass, 'after_transaction_end')
    def event_after_transaction_end(
        _session, transaction: sa_orm.SessionTransaction
    ) -> None:
        if transaction.nested:
            if transaction.parent and transaction.parent.nested:
                rich_console.print("[bold]transaction:[/] END (double nested)")
            else:
                rich_console.print("[bold]transaction:[/] END (nested)")
        else:
            rich_console.print("[bold]transaction:[/] END (outer)")
        print_stack(0, 5)

    yield

    event.remove(models.Model, 'init', event_init)
    event.remove(
        DatabaseSessionClass, 'transient_to_pending', event_transient_to_pending
    )
    event.remove(
        DatabaseSessionClass, 'pending_to_transient', event_pending_to_transient
    )
    event.remove(
        DatabaseSessionClass, 'pending_to_persistent', event_pending_to_persistent
    )
    event.remove(
        DatabaseSessionClass, 'loaded_as_persistent', event_loaded_as_persistent
    )
    event.remove(
        DatabaseSessionClass, 'persistent_to_transient', event_persistent_to_transient
    )
    event.remove(
        DatabaseSessionClass, 'persistent_to_deleted', event_persistent_to_deleted
    )
    event.remove(DatabaseSessionClass, 'deleted_to_detached', event_deleted_to_detached)
    event.remove(
        DatabaseSessionClass, 'persistent_to_detached', event_persistent_to_detached
    )
    event.remove(
        DatabaseSessionClass, 'detached_to_persistent', event_detached_to_persistent
    )
    event.remove(
        DatabaseSessionClass, 'deleted_to_persistent', event_deleted_to_persistent
    )
    event.remove(DatabaseSessionClass, 'do_orm_execute', event_do_orm_execute)
    event.remove(DatabaseSessionClass, 'after_begin', event_after_begin)
    event.remove(DatabaseSessionClass, 'after_commit', event_after_commit)
    event.remove(DatabaseSessionClass, 'after_flush', event_after_flush)
    event.remove(DatabaseSessionClass, 'after_rollback', event_after_rollback)
    event.remove(DatabaseSessionClass, 'after_soft_rollback', event_after_soft_rollback)
    event.remove(
        DatabaseSessionClass, 'after_transaction_create', event_after_transaction_create
    )
    event.remove(
        DatabaseSessionClass, 'after_transaction_end', event_after_transaction_end
    )


def _truncate_all_tables(engine: sa.Engine) -> None:
    """Truncate all tables in the given database engine."""
    deadlock_retries = 0
    while True:
        with engine.begin() as transaction:
            try:
                transaction.execute(
                    sa.text(
                        '''
                        DO $$
                        DECLARE tablenames text;
                        BEGIN
                            tablenames := string_agg(
                                quote_ident(schemaname)
                                || '.'
                                || quote_ident(tablename), ', '
                            ) FROM pg_tables WHERE schemaname = 'public';
                            EXECUTE
                                'TRUNCATE TABLE ' || tablenames || ' RESTART IDENTITY';
                        END; $$'''
                    )
                )
                break
            except sa_exc.OperationalError:
                # The TRUNCATE TABLE call will occasionally have a deadlock when the
                # background server process has not finalised the transaction.
                # SQLAlchemy recasts :exc:`psycopg.errors.DeadlockDetected` as
                # :exc:`sqlalchemy.exc.OperationalError`. Pytest will show as::
                #
                #     ERROR <filename> - sqlalchemy.exc.OperationalError:
                #     (psycopg.errors.DeadlockDetected) deadlock detected
                #     DETAIL: Process <pid1> waits for AccessExclusiveLock on relation
                #     <rel1> of database <db>; blocked by process <pid2>. Process <pid2>
                #     waits for AccessShareLock on relation <rel2> of database <db>;
                #     blocked by process <pid1>.
                #
                # We overcome the deadlock by rolling back the transaction, sleeping a
                # second and attempting to truncate again, retrying two more times. If
                # the deadlock remains unresolved, we raise the error to pytest. We are
                # not explicitly checking for OperationalError wrapping DeadlockDetected
                # on the assumption that this retry is safe for all operational errors.
                # Any new type of non-transient error will be reported by the final
                # raise.
                if (deadlock_retries := deadlock_retries + 1) > MAX_DEADLOCK_RETRIES:
                    raise
                transaction.rollback()
            time.sleep(1)


@pytest.fixture(scope='session')
def database(funnel, models, request: pytest.FixtureRequest, app: Flask) -> SQLAlchemy:
    """Provide a database structure."""
    with app.app_context():
        models.db.create_all()
        funnel.redis_store.flushdb()
        # Iterate through all database engines and empty their tables, just in case
        # a previous test run failed and left stale data in the database
        for engine in models.db.engines.values():
            _truncate_all_tables(engine)

    @request.addfinalizer
    def drop_tables() -> None:
        with app.app_context():
            models.db.drop_all()

    return models.db


@pytest.fixture
def db_session_truncate(
    funnel, app, database: SQLAlchemy, app_context
) -> Generator[scoped_session, None, None]:
    """Empty the database after each use of the fixture."""
    yield database.session
    sa_orm.close_all_sessions()

    # Iterate through all database engines and empty their tables
    for engine in database.engines.values():
        _truncate_all_tables(engine)

    # Clear Redis db too
    funnel.redis_store.flushdb()


@dataclass
class BindConnectionTransaction:
    engine: sa.engine.Engine
    connection: Any
    transaction: Any


class BoundSession(FsaSession):
    def __init__(
        self,
        db: SQLAlchemy,
        bindcts: dict[str | None, BindConnectionTransaction],
        **kwargs: Any,
    ) -> None:
        super().__init__(db, **kwargs)
        self.bindcts = bindcts

    def get_bind(
        self,
        mapper: Any | None = None,
        clause: Any | None = None,
        bind: sa.engine.Engine | sa.engine.Connection | None = None,
        **_kwargs: Any,
    ) -> sa.engine.Engine | sa.engine.Connection:
        if bind is not None:
            return bind
        if mapper is not None:
            mapper_insp: sa_orm.Mapper = sa.inspect(mapper)
            table = mapper_insp.local_table
            if isinstance(table, sa.Table):
                # This is always a table when using SQLAlchemy declarative with
                # __table__ or __tablename__ in a model
                bind_key = table.metadata.info.get('bind_key')
                return self.bindcts[bind_key].connection
            raise NotImplementedError(  # pragma: no cover
                f"Unexpected mapper local_table type: {table!r}"
            )
        if isinstance(clause, sa.Table):
            bind_key = clause.metadata.info.get('bind_key')
            return self.bindcts[bind_key].connection
        return self.bindcts[None].connection


@pytest.fixture
def db_session_rollback(
    funnel, app: Flask, database: SQLAlchemy, app_context: AppContext
) -> Generator[scoped_session, None, None]:
    """Create a nested transaction for the test and rollback after."""
    original_session = database.session

    bindcts: dict[str | None, BindConnectionTransaction] = {}
    for bind, engine in database.engines.items():
        connection = engine.connect()
        transaction = connection.begin()
        bindcts[bind] = BindConnectionTransaction(engine, connection, transaction)
    database.session = database._make_scoped_session(  # pylint: disable=W0212
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


@pytest.fixture
def db_session(request: pytest.FixtureRequest) -> scoped_session:
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
    * An individual test can be decorated with ``@pytest.mark.dbcommit``
    * A test module or package can override the ``db_session`` fixture to return one of
      the underlying fixtures, thereby overriding both of the above behaviours
    """
    return request.getfixturevalue(
        db_session_implementations[
            (
                'truncate'
                if request.node.get_closest_marker('dbcommit')
                else cast(str, request.config.getoption('--dbsession'))
            )
        ]
    )


class TestClient(FlaskClient):
    """Dummy subclass used for corrected type hints as FlaskClient is not a Generic."""

    # Tell Pytest this class isn't a test
    __test__ = False

    if TYPE_CHECKING:

        def open(  # type: ignore[override]
            self,
            *args: Any,
            buffered: bool = False,
            follow_redirects: bool = False,
            **kwargs: Any,
        ) -> TestResponse: ...

        def get(self, *args: Any, **kw: Any) -> TestResponse:  # type: ignore[override]
            ...

        def post(self, *args: Any, **kw: Any) -> TestResponse:  # type: ignore[override]
            ...

        def put(self, *args: Any, **kw: Any) -> TestResponse:  # type: ignore[override]
            ...

        def delete(  # type: ignore[override]
            self, *args: Any, **kw: Any
        ) -> TestResponse: ...

        def patch(  # type: ignore[override]
            self, *args: Any, **kw: Any
        ) -> TestResponse: ...

        def options(  # type: ignore[override]
            self, *args: Any, **kw: Any
        ) -> TestResponse: ...

        def head(self, *args: Any, **kw: Any) -> TestResponse:  # type: ignore[override]
            ...

        def trace(  # type: ignore[override]
            self, *args: Any, **kw: Any
        ) -> TestResponse: ...


@pytest.fixture
def client(app: Flask, db_session: scoped_session) -> TestClient:
    """Provide a test client that commits the db session before any action."""
    client = TestClient(app, TestResponse, use_cookies=True)
    client_open = client.open

    def commit_before_open(*args: Any, **kwargs: Any) -> TestResponse:
        db_session.commit()
        return client_open(*args, **kwargs)

    client.open = commit_before_open  # type: ignore[method-assign]
    return client


class BackgroundWorkerProtocol(Protocol):
    """Background worker for typeguard."""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> None: ...


class LiveServerProtocol(Protocol):
    """Live server for typeguard."""

    background_worker: BackgroundWorker
    transport_calls: CapturedCalls
    url: str
    urls: list[str]


@pytest.fixture(scope='session')
def live_server(
    funnel_devtest, app: Flask, database: SQLAlchemy
) -> Generator[LiveServerProtocol, None, None]:
    """Run application in a separate process."""
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
            yield cast(
                LiveServerProtocol,
                SimpleNamespace(
                    background_worker=server,
                    transport_calls=server.calls,
                    url=f'{scheme}://{app.config["SERVER_NAME"]}/',
                    urls=[
                        f'{scheme}://{m_app.config["SERVER_NAME"]}/'
                        for m_app in funnel_devtest.devtest_app.apps_by_host.values()
                    ],
                ),
            )


@pytest.fixture
def csrf_token(app: Flask, client: TestClient) -> str:
    """Supply a CSRF token for use in form submissions."""
    field_name = app.config.get('WTF_CSRF_FIELD_NAME', 'csrf_token')
    with app.test_request_context():
        token = generate_csrf()
        assert field_name in session
        session_token = session[field_name]
    with client.session_transaction() as client_session:
        client_session[field_name] = session_token
    return token


class LoginFixtureProtocol(Protocol):
    def as_(self, user: funnel_models.User) -> None: ...

    def logout(self) -> None: ...


@pytest.fixture
def login(
    app: Flask, client: TestClient, db_session: scoped_session
) -> LoginFixtureProtocol:
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
        client.delete_cookie('lastuser', domain=app.config['LASTUSER_COOKIE_DOMAIN'])

    return SimpleNamespace(as_=as_, logout=logout)  # pyright: ignore[reportReturnType]


# MARK: Sample data --------------------------------------------------------------------

# These names are adapted from the Discworld universe. Backstories can be found at:
# * https://discworld.fandom.com/
# * https://wiki.lspace.org/


# MARK: Users


class GetUserProtocol(Protocol):
    usermap: dict[str, str]

    def __call__(self, user: str) -> funnel_models.User: ...


@pytest.fixture
def getuser(request: pytest.FixtureRequest) -> GetUserProtocol:
    """Get a user fixture by their name."""
    # spell-checker: disable
    usermap = {
        "Twoflower": 'user_twoflower',
        "Rincewind": 'user_rincewind',
        "Death": 'user_death',
        "Mort": 'user_mort',
        "Susan Sto Helit": 'user_susan',
        "Susan": 'user_susan',
        "Lu-Tze": 'user_lutze',
        "Mustrum Ridcully": 'user_ridcully',
        "Ridcully": 'user_ridcully',
        "Mustrum": 'user_ridcully',
        "The Librarian": 'user_librarian',
        "Librarian": 'user_librarian',
        "Ponder Stibbons": 'user_ponder_stibbons',
        "Ponder": 'user_ponder_stibbons',
        "Stibbons": 'user_ponder_stibbons',
        "Havelock Vetinari": 'user_vetinari',
        "Havelock": 'user_vetinari',
        "Vetinari": 'user_vetinari',
        "Sam Vimes": 'user_vimes',
        "Vimes": 'user_vimes',
        "Carrot Ironfoundersson": 'user_carrot',
        "Carrot": 'user_carrot',
        "Angua von Überwald": 'user_angua',
        "CMOT Dibbler": 'user_dibbler',
        "Dibbler": 'user_dibbler',
        "Wolfgang von Überwald": 'user_wolfgang',
        "Wolfgang": 'user_wolfgang',
        "Om": 'user_om',
    }
    # spell-checker: enable

    def func(user: str) -> funnel_models.User:
        if user not in usermap:
            pytest.fail(f"No user fixture named {user}")
        return request.getfixturevalue(usermap[user])

    func = cast(GetUserProtocol, func)
    # Aid for tests
    func.usermap = usermap
    return func


@pytest.fixture
def user_twoflower(models, db_session: scoped_session) -> funnel_models.User:
    """
    Twoflower is a tourist from the Agatean Empire who goes on adventures.

    As a tourist unfamiliar with local customs, Twoflower represents our naive user,
    having only made a user account but not having picked a username or made any other
    affiliations.
    """
    user = models.User(fullname="Twoflower")
    db_session.add(user)
    return user


@pytest.fixture
def user_rincewind(models, db_session: scoped_session) -> funnel_models.User:
    """
    Rincewind is a wizard and a former member of Unseen University.

    Rincewind is Twoflower's guide in the first two books, and represents our fully
    initiated user in tests.
    """
    user = models.User(username='rincewind', fullname="Rincewind")
    db_session.add(user)
    return user


@pytest.fixture
def user_death(models, db_session: scoped_session) -> funnel_models.User:
    """
    Death is the epoch user, present at the beginning and always having the last word.

    Since Death predates all other users in tests, any call to `merge_accounts` or
    `migrate_account` always transfers assets to Death. The fixture has joined_at set
    to the epoch to represent this. Death is also a site admin.
    """
    user = models.User(
        username='death',
        fullname="Death",
        joined_at=datetime(1970, 1, 1, tzinfo=UTC),
    )
    user.is_protected = True
    db_session.add(user)
    return user


@pytest.fixture
def user_mort(models, db_session: scoped_session) -> funnel_models.User:
    """
    Mort is Death's apprentice, and a site admin in tests.

    Mort has a joined_at in the past (the publication date of the book), granting
    priority when merging user accounts. Unlike Death, Mort does not have a username or
    profile, so Mort will acquire it from a merged user.
    """
    user = models.User(fullname="Mort", joined_at=datetime(1987, 11, 12, tzinfo=UTC))
    db_session.add(user)
    return user


@pytest.fixture
def user_susan(models, db_session: scoped_session) -> funnel_models.User:
    """
    Susan Sto Helit (also written Sto-Helit) is Death's grand daughter.

    Susan inherits Death's role as a site admin and plays a correspondent with Mort.
    """
    user = models.User(username='susan', fullname="Susan Sto Helit")
    db_session.add(user)
    return user


@pytest.fixture
def user_lutze(models, db_session: scoped_session) -> funnel_models.User:
    """
    Lu-Tze is a history monk and sweeper at the Monastery of Oi-Dong.

    Lu-Tze plays the role of a site editor, cleaning up after messy users.
    """
    user = models.User(username='lu_tze', fullname="Lu-Tze")
    db_session.add(user)
    return user


@pytest.fixture
def user_ridcully(models, db_session: scoped_session) -> funnel_models.User:
    """
    Mustrum Ridcully, archchancellor of Unseen University.

    Ridcully serves as an owner of the Unseen University organization in tests.
    """
    user = models.User(username='ridcully', fullname="Mustrum Ridcully")
    db_session.add(user)
    return user


@pytest.fixture
def user_librarian(models, db_session: scoped_session) -> funnel_models.User:
    """
    Librarian of Unseen University, currently an orangutan.

    The Librarian serves as an admin of the Unseen University organization in tests.
    """
    user = models.User(username='librarian', fullname="The Librarian")
    db_session.add(user)
    return user


@pytest.fixture
def user_ponder_stibbons(models, db_session: scoped_session) -> funnel_models.User:
    """
    Ponder Stibbons, maintainer of Hex, the computer powered by an Anthill Inside.

    Admin of UU org.
    """
    user = models.User(username='ponder_stibbons', fullname="Ponder Stibbons")
    db_session.add(user)
    return user


@pytest.fixture
def user_vetinari(models, db_session: scoped_session) -> funnel_models.User:
    """
    Havelock Vetinari, patrician (aka dictator) of Ankh-Morpork.

    Co-owner of the City Watch organization in our tests.
    """
    user = models.User(username='vetinari', fullname="Havelock Vetinari")
    db_session.add(user)
    return user


@pytest.fixture
def user_vimes(models, db_session: scoped_session) -> funnel_models.User:
    """
    Samuel Vimes, commander of the Ankh-Morpork City Watch.

    Co-owner of the City Watch organization in our tests.
    """
    user = models.User(username='vimes', fullname="Sam Vimes")
    db_session.add(user)
    return user


@pytest.fixture
def user_carrot(models, db_session: scoped_session) -> funnel_models.User:
    """
    Carrot Ironfoundersson, captain of the Ankh-Morpork City Watch.

    Admin of the organization in our tests.
    """
    user = models.User(username='carrot', fullname="Carrot Ironfoundersson")
    db_session.add(user)
    return user


@pytest.fixture
def user_angua(models, db_session: scoped_session) -> funnel_models.User:
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


@pytest.fixture
def user_dibbler(models, db_session: scoped_session) -> funnel_models.User:
    """
    Cut Me Own Throat (or C.M.O.T) Dibbler, huckster who exploits small opportunities.

    Represents the spammer in our tests, from spam comments to spam projects.
    """
    user = models.User(username='dibbler', fullname="CMOT Dibbler")
    db_session.add(user)
    return user


@pytest.fixture
def user_wolfgang(models, db_session: scoped_session) -> funnel_models.User:
    """
    Wolfgang von Überwald, brother of Angua, violent shapeshifter.

    Represents an attacker who changes appearance by changing identifiers or making
    sockpuppet user accounts.
    """
    user = models.User(username='wolfgang', fullname="Wolfgang von Überwald")
    db_session.add(user)
    return user


@pytest.fixture
def user_om(models, db_session: scoped_session) -> funnel_models.User:
    """
    Great God Om of the theocracy of Omnia, who has lost his believers.

    Moves between having a user account and an org account in tests, creating a new user
    account for Brutha, the last believer.
    """
    user = models.User(username='omnia', fullname="Om")
    db_session.add(user)
    return user


# MARK: Organizations


@pytest.fixture
def org_ankhmorpork(
    models, db_session: scoped_session, user_vetinari: funnel_models.User
) -> funnel_models.Organization:
    """
    City of Ankh-Morpork, here representing the government rather than location.

    Havelock Vetinari is the Patrician (aka dictator), and sponsors various projects to
    develop the city.
    """
    org = models.Organization(
        name='ankh_morpork', title="Ankh-Morpork", owner=user_vetinari
    )
    db_session.add(org)
    return org


@pytest.fixture
def org_uu(
    models,
    db_session: scoped_session,
    user_ridcully: funnel_models.User,
    user_librarian: funnel_models.User,
    user_ponder_stibbons: funnel_models.User,
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
        models.AccountMembership(
            account=org,
            member=user_librarian,
            is_admin=True,
            granted_by=user_ridcully,
        )
    )
    db_session.add(
        models.AccountMembership(
            account=org,
            member=user_ponder_stibbons,
            is_admin=True,
            granted_by=user_ridcully,
        )
    )
    return org


@pytest.fixture
def org_citywatch(
    models,
    db_session: scoped_session,
    user_vetinari: funnel_models.User,
    user_vimes: funnel_models.User,
    user_carrot: funnel_models.User,
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
        name='city_watch', title="City Watch", owner=user_vetinari
    )
    db_session.add(org)
    db_session.add(
        models.AccountMembership(
            account=org,
            member=user_vimes,
            is_owner=True,
            granted_by=user_vetinari,
        )
    )
    db_session.add(
        models.AccountMembership(
            account=org, member=user_carrot, is_admin=True, granted_by=user_vimes
        )
    )
    return org


# MARK: Projects

# Fixtures from this point on drift away from Discworld, to reflect the unique contours
# of the product being tested. Maintaining fidelity to Discworld is hard.


@pytest.fixture
def project_expo2010(
    models,
    db_session: scoped_session,
    org_ankhmorpork: funnel_models.Organization,
    user_vetinari: funnel_models.User,
) -> funnel_models.Project:
    """Ankh-Morpork hosts its 2010 expo."""
    db_session.flush()

    project = models.Project(
        account=org_ankhmorpork,
        created_by=user_vetinari,
        title="Ankh-Morpork 2010",
        tagline="Welcome to Ankh-Morpork, tourists!",
        description="The city doesn't have tourists. Let’s change that.",
    )
    db_session.add(project)
    return project


@pytest.fixture
def project_expo2011(
    models,
    db_session: scoped_session,
    org_ankhmorpork: funnel_models.Organization,
    user_vetinari: funnel_models.User,
) -> funnel_models.Project:
    """Ankh-Morpork hosts its 2011 expo."""
    db_session.flush()

    project = models.Project(
        account=org_ankhmorpork,
        created_by=user_vetinari,
        title="Ankh-Morpork 2011",
        tagline="Welcome back, our pub’s changed",
        description="The Broken Drum is gone, but we have The Mended Drum now.",
    )
    db_session.add(project)
    return project


@pytest.fixture
def project_ai1(
    models,
    db_session: scoped_session,
    org_uu: funnel_models.Organization,
    user_ponder_stibbons: funnel_models.User,
) -> funnel_models.Project:
    """
    Anthill Inside conference, hosted by Unseen University (an inspired event).

    Based on Soul Music, which features the first appearance of Hex, published 1994.
    """
    db_session.flush()

    project = models.Project(
        account=org_uu,
        created_by=user_ponder_stibbons,
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


@pytest.fixture
def project_ai2(
    models,
    db_session: scoped_session,
    org_uu: funnel_models.Organization,
    user_ponder_stibbons: funnel_models.User,
) -> funnel_models.Project:
    """
    Anthill Inside conference, hosted by Unseen University (an inspired event).

    Based on Interesting Times.
    """
    db_session.flush()

    project = models.Project(
        account=org_uu,
        created_by=user_ponder_stibbons,
        title="Interesting Times",
        tagline="Hex invents parts for itself",
        description="Hex has become a lot more complex, and is constantly reinventing"
        " itself, meaning several new components of it are mysteries to those at UU.",
    )
    db_session.add(project)
    return project


# MARK: Client apps


@pytest.fixture
def client_hex(
    models, db_session: scoped_session, org_uu: funnel_models.Organization
) -> funnel_models.AuthClient:
    """
    Hex, supercomputer at Unseen University, powered by an Anthill Inside.

    Owned by UU (owner) and administered by Ponder Stibbons (no corresponding role).
    """
    auth_client = models.AuthClient(
        title="Hex",
        account=org_uu,
        confidential=True,
        website='https://example.org/',
        redirect_uris=['https://example.org/callback'],
    )
    db_session.add(auth_client)
    return auth_client


class CredProtocol(Protocol):
    cred: funnel_models.AuthClientCredential
    secret: str


@pytest.fixture
def client_hex_credential(
    models, db_session: scoped_session, client_hex: funnel_models.AuthClient
) -> CredProtocol:
    cred, secret = models.AuthClientCredential.new(client_hex)
    db_session.add(cred)
    return cast(CredProtocol, SimpleNamespace(cred=cred, secret=secret))


@pytest.fixture
def all_fixtures(  # pylint: disable=too-many-locals
    db_session: scoped_session,
    user_twoflower: funnel_models.User,
    user_rincewind: funnel_models.User,
    user_death: funnel_models.User,
    user_mort: funnel_models.User,
    user_susan: funnel_models.User,
    user_lutze: funnel_models.User,
    user_ridcully: funnel_models.User,
    user_librarian: funnel_models.User,
    user_ponder_stibbons: funnel_models.User,
    user_vetinari: funnel_models.User,
    user_vimes: funnel_models.User,
    user_carrot: funnel_models.User,
    user_angua: funnel_models.User,
    user_dibbler: funnel_models.User,
    user_wolfgang: funnel_models.User,
    user_om: funnel_models.User,
    org_ankhmorpork: funnel_models.User,
    org_uu: funnel_models.User,
    org_citywatch: funnel_models.User,
    project_expo2010: funnel_models.User,
    project_expo2011: funnel_models.User,
    project_ai1: funnel_models.User,
    project_ai2: funnel_models.User,
    client_hex: funnel_models.User,
) -> SimpleNamespace:
    """Return All Discworld fixtures at once."""
    db_session.commit()
    return SimpleNamespace(**locals())


# MARK: Old fixtures, to be removed when tests are updated -----------------------------


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
        'test_org_owner': {
            'name': "test_org_owner",
            'fullname': "Test User 2",
        },
        'test_org_admin': {
            'name': "test_org_admin",
            'fullname': "Test User 3",
        },
    }
}


@pytest.fixture
def new_user(models, db_session: scoped_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['testuser'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_user2(models, db_session: scoped_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['testuser2'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_user_owner(models, db_session: scoped_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['test_org_owner'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_user_admin(models, db_session: scoped_session) -> funnel_models.User:
    user = models.User(**TEST_DATA['users']['test_org_admin'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_organization(
    models,
    db_session: scoped_session,
    new_user_owner: funnel_models.User,
    new_user_admin: funnel_models.User,
) -> funnel_models.Organization:
    org = models.Organization(owner=new_user_owner, title="Test org", name='test_org')
    db_session.add(org)

    admin_membership = models.AccountMembership(
        account=org,
        member=new_user_admin,
        is_admin=True,
        granted_by=new_user_owner,
    )
    db_session.add(admin_membership)
    db_session.commit()
    return org


@pytest.fixture
def new_team(
    models,
    db_session: scoped_session,
    new_user: funnel_models.User,
    new_organization: funnel_models.Organization,
) -> funnel_models.Team:
    team = models.Team(title="Owners", account=new_organization)
    db_session.add(team)
    team.users.append(new_user)
    db_session.commit()
    return team


@pytest.fixture
def new_project(
    models,
    db_session: scoped_session,
    new_organization: funnel_models.Organization,
    new_user: funnel_models.User,
) -> funnel_models.Project:
    project = models.Project(
        account=new_organization,
        created_by=new_user,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def new_project2(
    models,
    db_session: scoped_session,
    new_organization: funnel_models.Organization,
    new_user_owner: funnel_models.User,
) -> funnel_models.Project:
    project = models.Project(
        account=new_organization,
        created_by=new_user_owner,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def new_main_label(
    models, db_session: scoped_session, new_project: funnel_models.Project
) -> funnel_models.Label:
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


@pytest.fixture
def new_main_label_unrestricted(
    models, db_session: scoped_session, new_project: funnel_models.Project
) -> funnel_models.Label:
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


@pytest.fixture
def new_label(
    models, db_session: scoped_session, new_project: funnel_models.Project
) -> funnel_models.Label:
    label_b = models.Label(title="Label B", icon_emoji="🔟", project=new_project)
    new_project.all_labels.append(label_b)
    db_session.add(label_b)
    db_session.commit()
    return label_b


@pytest.fixture
def new_proposal(
    models,
    db_session: scoped_session,
    new_user: funnel_models.User,
    new_project: funnel_models.Project,
) -> funnel_models.Proposal:
    proposal = models.Proposal(
        created_by=new_user,
        project=new_project,
        title="Test Proposal",
        body="Test proposal description",
    )
    db_session.add(proposal)
    db_session.commit()
    return proposal


@pytest.fixture
def fail_with_diff() -> Callable[[str, str], None]:
    def func(left: str, right: str) -> None:
        if left != right:
            difference = unified_diff(left.split('\n'), right.split('\n'))
            msg = [line for line in difference if not line.startswith(' ')]
            pytest.fail('\n'.join(msg), pytrace=False)

    return func
