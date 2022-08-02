"""Test configuration and fixtures."""

from datetime import datetime
from types import MethodType, SimpleNamespace
from typing import List, NamedTuple, Optional
import logging
import re

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session as DatabaseSessionClass
from sqlalchemy.orm import close_all_sessions

from flask.testing import FlaskClient
from flask.wrappers import Response

from lxml.html import FormElement, HtmlElement, fromstring  # nosec  # noqa: S410
from pytz import utc
import pytest

from funnel import app as funnel_app
from funnel import redis_store
from funnel.models import (
    AuthClient,
    AuthClientCredential,
    Label,
    Organization,
    OrganizationMembership,
    Project,
    Proposal,
    Team,
    User,
    db,
)

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


class MetaRefreshContent(NamedTuple):
    """Timeout and optional URL in a Meta Refresh tag."""

    timeout: int
    url: Optional[str] = None


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

    _parsed_html: Optional[HtmlElement] = None

    @property
    def html(self) -> HtmlElement:
        """Return the parsed HTML tree."""
        if self._parsed_html is None:
            self._parsed_html = fromstring(self.data)

            # add click method to all links
            def _click(self, client, **kwargs):  # pylint: disable=redefined-outer-name
                # `self` is the `a` element here
                path = self.attrib['href']
                return client.get(path, **kwargs)

            for link in self._parsed_html.iter('a'):
                link.click = MethodType(_click, link)  # type: ignore[attr-defined]

            # add submit method to all forms
            def _submit(
                self, client, path=None, **kwargs
            ):  # pylint: disable=redefined-outer-name
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
    def forms(self) -> List[FormElement]:
        """
        Return list of all forms in the document.

        Contains the LXML form type as documented at http://lxml.de/lxmlhtml.html#forms
        with an additional `.submit(client)` method to submit the form.
        """
        return self.html.forms

    def form(
        self, id_: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[FormElement]:
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

    def links(self, selector: str = 'a') -> List[HtmlElement]:
        """Get all the links matching the given CSS selector."""
        return self.html.cssselect(selector)

    def link(self, selector: str = 'a') -> Optional[HtmlElement]:
        """Get first link matching the given CSS selector."""
        links = self.links(selector)
        if links:
            return links[0]
        return None

    @property
    def metarefresh(self) -> Optional[MetaRefreshContent]:
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


# --- Pytest config --------------------------------------------------------------------


def pytest_addoption(parser):
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
    )

    def sort_key(item):
        module_file = item.module.__file__
        for counter, path in enumerate(test_order):
            if path in module_file:
                return (counter, module_file)
        return (-1, module_file)

    items.sort(key=sort_key)


# --- Fixtures -------------------------------------------------------------------------


@pytest.fixture(scope='session')
def app():
    """App as a fixture to avoid imports in tests."""
    return funnel_app


@pytest.fixture(scope='session')
def _database_events(logger):
    """
    Fixture to report database session events for debugging a test.

    If a test is exhibiting unusual behaviour, add this fixture to trace db events, and
    call the test with cli option ``--log-cli-level=INFO`` (or lower)::

        @pytest.mark.usefixtures('_database_events')
        def test_whatever():
            ...
    """

    def safe_repr(entity):
        try:
            return repr(entity)
        except Exception:  # noqa: B902  # pylint: disable=broad-except
            if hasattr(entity, '__class__'):
                return f'{entity.__class__.__qualname__}(class-repr-error)'
            if hasattr(entity, '__name__'):
                return f'{entity.__name__}(repr-error)'
            return 'repr-error'

    @event.listens_for(db.Model, 'init', propagate=True)
    def event_init(obj, args, kwargs):
        rargs = ', '.join(safe_repr(_a) for _a in args)
        rkwargs = ', '.join(f'{_k}={safe_repr(_v)}' for _k, _v in kwargs.items())
        rparams = f'{rargs, rkwargs}' if rargs else rkwargs
        logging.info("obj: new: %s(%s)", obj.__class__.__qualname__, rparams)

    @event.listens_for(DatabaseSessionClass, 'transient_to_pending')
    def event_transient_to_pending(_session, obj):
        logging.info("obj: transient to pending: %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'pending_to_transient')
    def event_pending_to_transient(_session, obj):
        logging.info("obj: pending to transient: %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'pending_to_persistent')
    def event_pending_to_persistent(_session, obj):
        logging.info("obj: pending to persistent: %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'loaded_as_persistent')
    def event_loaded_as_persistent(_session, obj):
        logging.info("obj: loaded as persistent %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'persistent_to_transient')
    def event_persistent_to_transient(_session, obj):
        logging.info("obj: persistent to transient: %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'persistent_to_deleted')
    def event_persistent_to_deleted(_session, obj):
        logging.info("obj: persistent to deleted %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'deleted_to_detached')
    def event_deleted_to_detached(_session, obj):
        i = inspect(obj)
        logging.info(
            "obj: deleted to detached: %s/%s", obj.__class__.__qualname__, i.identity
        )

    @event.listens_for(DatabaseSessionClass, 'persistent_to_detached')
    def event_persistent_to_detached(_session, obj):
        i = inspect(obj)
        logging.info(
            "obj: persistent to detached: %s/%s", obj.__class__.__qualname__, i.identity
        )

    @event.listens_for(DatabaseSessionClass, 'detached_to_persistent')
    def event_detached_to_persistent(_session, obj):
        logging.info("obj: detached to persistent: %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'deleted_to_persistent')
    def event_deleted_to_persistent(session, obj):
        logging.info("obj: deleted to persistent: %s", safe_repr(obj))

    @event.listens_for(DatabaseSessionClass, 'do_orm_execute')
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
        logging.info(
            "exec: %s: %s",
            orm_execute_state.bind_mapper.class_.__qualname__
            if orm_execute_state.bind_mapper
            else None,
            ', '.join(state_is),
        )

    @event.listens_for(DatabaseSessionClass, 'after_begin')
    def event_after_begin(_session, _transaction, _connection):
        logging.info("session: BEGIN")

    @event.listens_for(DatabaseSessionClass, 'after_commit')
    def event_after_commit(_session):
        logging.info("session: COMMIT")

    @event.listens_for(DatabaseSessionClass, 'after_flush')
    def event_after_flush(_session, _flush_context):
        logging.info("session: FLUSH")

    @event.listens_for(DatabaseSessionClass, 'after_rollback')
    def event_after_rollback(_session):
        logging.info("session: ROLLBACK")

    @event.listens_for(DatabaseSessionClass, 'after_soft_rollback')
    def event_after_soft_rollback(_session, _previous_transaction):
        logging.info("session: SOFT ROLLBACK")


@pytest.fixture(scope='session')
def database(request, app):
    """Provide a database structure."""
    with app.app_context():
        db.create_all()
        redis_store.flushdb()

    @request.addfinalizer
    def drop_tables():
        with app.app_context():
            db.drop_all()

    return db


@pytest.fixture(scope='session')
def _db(database):  # noqa: PT005
    """Database fixture required by pytest-flask-sqlalchemy (unused)."""
    # Also see pyproject.toml for mock configuration
    return database


@pytest.fixture()
def db_session_truncate(app, database):
    """Empty the database after each use of the fixture."""
    yield database.session
    close_all_sessions()

    # Iterate through all database engines and empty their tables
    for bind in [None] + list(app.config.get('SQLALCHEMY_BINDS') or ()):
        engine = database.get_engine(app=app, bind=bind)
        with engine.begin() as connection:
            connection.execute(
                '''
                DO $$
                DECLARE tablenames text;
                BEGIN
                    tablenames := string_agg(
                        quote_ident(schemaname) || '.' || quote_ident(tablename),
                        ', ')
                        FROM pg_tables WHERE schemaname = 'public';
                    EXECUTE 'TRUNCATE TABLE ' || tablenames || ' RESTART IDENTITY';
                END; $$
            '''
            )

    # Clear Redis db too
    redis_store.flushdb()


@pytest.fixture()
def db_session_rollback(database):
    """Create a nested transaction for the test and rollback after."""
    db_connection = database.engine.connect()
    original_session = database.session
    transaction = db_connection.begin()
    database.session = database.create_scoped_session(
        options={'bind': db_connection, 'binds': {}}
    )

    # For handling tests that actually call `session.rollback()`, we use a SQL savepoint
    # and add an event handler that restarts the savepoint. SQLAlchemy 1.4 deprecated
    # session.commit() being used to commit a savepoint, and 2.0 will remove it,
    # potentially breaking this fixture. It will need revision then.
    #
    # References:
    #
    # * 1.3: https://docs.sqlalchemy.org/en/13/orm/session_transaction.html
    #   #joining-a-session-into-an-external-transaction-such-as-for-test-suites
    # * 1.4: https://docs.sqlalchemy.org/en/14/orm/session_transaction.html
    #   #joining-a-session-into-an-external-transaction-such-as-for-test-suites

    savepoint = database.session.begin_nested()
    database.session.force_commit = database.session.commit
    database.session.force_rollback = database.session.rollback
    database.session.force_close = database.session.close

    # This is breaking in the new app context created in
    # `funnel.views.login_session.update_user_session_timestamp` in internal function
    # `mark_session_accessed_after_response` when it does a commit

    # database.session.commit = savepoint.commit
    # database.session.rollback = savepoint.rollback
    # database.session.close = savepoint.rollback

    @event.listens_for(database.session, 'after_transaction_end')
    def restart_savepoint(session, transaction_in):
        nonlocal savepoint
        if transaction_in.nested and not transaction_in.parent.nested:
            # This is a top-level savepoint, so restart it
            session.expire_all()
            savepoint = session.begin_nested()
            # database.session.commit = savepoint.commit
            # database.session.rollback = savepoint.rollback
            # database.session.close = savepoint.rollback

    yield database.session

    database.session.force_close()
    transaction.rollback()
    db_connection.close()
    database.session = original_session

    # Clear Redis db too
    redis_store.flushdb()


@pytest.fixture()
def db_session(request):
    """
    Database session fixture.

    This fixture may be overridden in another conftest.py to return one of the two
    available session fixtures:

    * ``db_session_truncate``: Which allows unmediated database access but empties table
      contents after each use
    * ``db_session_savepoint``: Which nests the session in a SAVEPOINT and rolls back
      after each use

    This version of the fixture uses the --dbsession command-line option to choose the
    base fixture.
    """
    return request.getfixturevalue(
        {
            'rollback': 'db_session_rollback',
            'truncate': 'db_session_truncate',
        }[request.config.getoption('--dbsession')]
    )


# Enable autouse to guard against tests that have implicit database access, or assume
# app context without a fixture
@pytest.fixture(autouse=True)
def _push_request_context(request):
    if 'app' not in request.fixturenames and 'db_session' not in request.fixturenames:
        yield
    else:
        app_fixture = request.getfixturevalue('app')

        with app_fixture.test_request_context():
            yield


@pytest.fixture()
def client(request, app, db_session):
    """Provide a test client."""
    with FlaskClient(app, ResponseWithForms, use_cookies=True) as test_client:
        yield test_client


@pytest.fixture()
def csrf_token(client):
    """Supply a CSRF token for use in form submissions."""
    return client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)


@pytest.fixture()
def login(app, client):
    """Provide a login fixture."""

    def as_(user):
        with client.session_transaction() as session:
            # TODO: This depends on obsolete code in views/login_session that replaces
            # cookie session authentication with db-backed authentication. It's long
            # pending removal
            session['userid'] = user.userid
        # Perform a request to convert the session userid into a UserSession
        client.get('/api/1/user/get')

    def logout():
        # TODO: Test this
        client.delete_cookie(
            client.server_name, 'lastuser', domain=app.config['LASTUSER_COOKIE_DOMAIN']
        )

    return SimpleNamespace(as_=as_, logout=logout)


@pytest.fixture()
def varfixture(request):
    """
    Return a variable fixture.

    Usage::

        @pytest.mark.parametrize('varfixture', ['fixture1', 'fixture2'], indirect=True)
        def test_me(varfixture) -> None:
            ...

    This fixture can also be ignored, and a test can access a variable fixture directly:

    1. Don't use `indirect=True`
    2. Accept `request` as a parameter
    3. Get the actual fixture with `request.getfixturevalue(varfixture)`
    """
    return request.getfixturevalue(request.param)


# --- Sample data: users, organizations, projects, etc ---------------------------------

# These names are adapted from the Discworld universe. Backstories can be found at:
# * https://discworld.fandom.com/
# * https://wiki.lspace.org/


# --- Users


@pytest.fixture()
def user_twoflower(db_session):
    """
    Twoflower is a tourist from the Agatean Empire who goes on adventures.

    As a tourist unfamiliar with local customs, Twoflower represents our naive user,
    having only made a user account but not having picked a username or made any other
    affiliations.
    """
    user = User(fullname="Twoflower")
    db_session.add(user)
    return user


@pytest.fixture()
def user_rincewind(db_session):
    """
    Rincewind is a wizard and a former member of Unseen University.

    Rincewind is Twoflower's guide in the first two books, and represents our fully
    initiated user in tests.
    """
    user = User(username='rincewind', fullname="Rincewind")
    db_session.add(user)
    return user


@pytest.fixture()
def user_death(db_session):
    """
    Death is the epoch user, present at the beginning and always having the last word.

    Since Death predates all other users in tests, any call to `merge_users` or
    `migrate_user` always transfers assets to Death. The fixture has created_at set to
    the epoch to represent this. Death is also a site admin.
    """
    user = User(
        username='death',
        fullname="Death",
        created_at=utc.localize(datetime(1970, 1, 1)),
    )
    db_session.add(user)
    return user


@pytest.fixture()
def user_mort(db_session):
    """
    Mort is Death's apprentice, and a site admin in tests.

    Mort has a created_at in the past (the publication date of the book), granting
    priority when merging user accounts. Unlike Death, Mort does not have a username or
    profile, so Mort will acquire it from a merged user.
    """
    user = User(fullname="Mort", created_at=utc.localize(datetime(1987, 11, 12)))
    db_session.add(user)
    return user


@pytest.fixture()
def user_susan(db_session):
    """
    Susan Sto Helit (also written Sto-Helit) is Death's grand daughter.

    Susan inherits Death's role as a site admin and plays a correspondent with Mort.
    """
    user = User(username='susan', fullname="Susan Sto Helit")
    db_session.add(user)
    return user


@pytest.fixture()
def user_lutze(db_session):
    """
    Lu-Tze is a history monk and sweeper at the Monastery of Oi-Dong.

    Lu-Tze plays the role of a site editor, cleaning up after messy users.
    """
    user = User(username='lu-tze', fullname="Lu-Tze")
    db_session.add(user)
    return user


@pytest.fixture()
def user_ridcully(db_session):
    """
    Mustrum Ridcully, archchancellor of Unseen University.

    Ridcully serves as an owner of the Unseen University organization in tests.
    """
    user = User(username='ridcully', fullname="Mustrum Ridcully")
    db_session.add(user)
    return user


@pytest.fixture()
def user_librarian(db_session):
    """
    Librarian of Unseen University, currently an orangutan.

    The Librarian serves as an admin of the Unseen University organization in tests.
    """
    user = User(username='librarian', fullname="The Librarian")
    db_session.add(user)
    return user


@pytest.fixture()
def user_ponder_stibbons(db_session):
    """
    Ponder Stibbons, maintainer of Hex, the computer powered by an Anthill Inside.

    Admin of UU org.
    """
    user = User(username='ponder-stibbons', fullname="Ponder Stibbons")
    db_session.add(user)
    return user


@pytest.fixture()
def user_vetinari(db_session):
    """
    Havelock Vetinari, patrician (aka dictator) of Ankh-Morpork.

    Co-owner of the City Watch organization in our tests.
    """
    user = User(username='vetinari', fullname="Havelock Vetinari")
    db_session.add(user)
    return user


@pytest.fixture()
def user_vimes(db_session):
    """
    Samuel Vimes, commander of the Ankh-Morpork City Watch.

    Co-owner of the City Watch organization in our tests.
    """
    user = User(username='vimes', fullname="Sam Vimes")
    db_session.add(user)
    return user


@pytest.fixture()
def user_carrot(db_session):
    """
    Carrot Ironfoundersson, captain of the Ankh-Morpork City Watch.

    Admin of the organization in our tests.
    """
    user = User(username='carrot', fullname="Carrot Ironfoundersson")
    db_session.add(user)
    return user


@pytest.fixture()
def user_angua(db_session):
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
    user = User(fullname="Angua von Überwald", locale='ie', auto_locale=False)
    db_session.add(user)
    return user


@pytest.fixture()
def user_dibbler(db_session):
    """
    Cut Me Own Throat (or C.M.O.T) Dibbler, huckster who exploits small opportunities.

    Represents the spammer in our tests, from spam comments to spam projects.
    """
    user = User(username='dibbler', fullname="CMOT Dibbler")
    db_session.add(user)
    return user


@pytest.fixture()
def user_wolfgang(db_session):
    """
    Wolfgang von Überwald, brother of Angua, violent shapeshifter.

    Represents an attacker who changes appearance by changing identifiers or making
    sockpuppet user accounts.
    """
    user = User(username='wolfgang', fullname="Wolfgang von Überwald")
    db_session.add(user)
    return user


@pytest.fixture()
def user_om(db_session):
    """
    Great God Om of the theocracy of Omnia, who has lost his believers.

    Moves between having a user account and an org account in tests, creating a new user
    account for Brutha, the last believer.
    """
    user = User(username='omnia', fullname="Om")
    db_session.add(user)
    return user


# --- Organizations


@pytest.fixture()
def org_ankhmorpork(db_session, user_vetinari):
    """
    City of Ankh-Morpork, here representing the government rather than location.

    Havelock Vetinari is the Patrician (aka dictator), and sponsors various projects to
    develop the city.
    """
    org = Organization(name='ankh-morpork', title="Ankh-Morpork", owner=user_vetinari)
    db_session.add(org)
    return org


@pytest.fixture()
def org_uu(db_session, user_ridcully, user_librarian, user_ponder_stibbons):
    """
    Unseen University is located in Ankh-Morpork.

    Staff:

    * Alberto Malich, founder emeritus (not listed here since no corresponding role)
    * Mustrum Ridcully, archchancellor (owner)
    * The Librarian, head of the library (admin)
    * Ponder Stibbons, Head of Inadvisably Applied Magic (admin)
    """
    org = Organization(name='UU', title="Unseen University", owner=user_ridcully)
    db_session.add(org)
    db_session.add(
        OrganizationMembership(
            organization=org,
            user=user_librarian,
            is_owner=False,
            granted_by=user_ridcully,
        )
    )
    db_session.add(
        OrganizationMembership(
            organization=org,
            user=user_ponder_stibbons,
            is_owner=False,
            granted_by=user_ridcully,
        )
    )
    return org


@pytest.fixture()
def org_citywatch(db_session, user_vetinari, user_vimes, user_carrot):
    """
    City Watch of Ankh-Morpork (a sub-organization).

    Staff:

    * Havelock Vetinari, Patrician of the city, legal owner but with no operating role
    * Sam Vimes, commander (owner)
    * Carrot Ironfoundersson, captain (admin)
    * Angua von Uberwald, corporal (unlisted, as there is no member role)
    """
    org = Organization(name='city-watch', title="City Watch", owner=user_vetinari)
    db_session.add(org)
    db_session.add(
        OrganizationMembership(
            organization=org, user=user_vimes, is_owner=True, granted_by=user_vetinari
        )
    )
    db_session.add(
        OrganizationMembership(
            organization=org, user=user_carrot, is_owner=False, granted_by=user_vimes
        )
    )
    return org


# --- Projects
# Fixtures from this point on drift away from Discworld, to reflect the unique contours
# of the product being tested. Maintaining fidelity to Discworld is hard.


@pytest.fixture()
def project_expo2010(db_session, org_ankhmorpork, user_vetinari):
    """Ankh-Morpork hosts its 2010 expo."""
    db_session.flush()

    project = Project(
        profile=org_ankhmorpork.profile,
        user=user_vetinari,
        title="Ankh-Morpork 2010",
        tagline="Welcome to Ankh-Morpork, tourists!",
        description="The city doesn't have tourists. Let's change that.",
    )
    db_session.add(project)
    return project


@pytest.fixture()
def project_expo2011(db_session, org_ankhmorpork, user_vetinari):
    """Ankh-Morpork hosts its 2011 expo."""
    db_session.flush()

    project = Project(
        profile=org_ankhmorpork.profile,
        user=user_vetinari,
        title="Ankh-Morpork 2011",
        tagline="Welcome back, our pub's changed",
        description="The Broken Drum is gone, but we have The Mended Drum now.",
    )
    db_session.add(project)
    return project


@pytest.fixture()
def project_ai1(db_session, org_uu, user_ponder_stibbons):
    """
    Anthill Inside conference, hosted by Unseen University (an inspired event).

    Based on Soul Music, which features the first appearance of Hex, published 1994.
    """
    db_session.flush()

    project = Project(
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
def project_ai2(db_session, org_uu, user_ponder_stibbons):
    """
    Anthill Inside conference, hosted by Unseen University (an inspired event).

    Based on Interesting Times.
    """
    db_session.flush()

    project = Project(
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
def client_hex(db_session, org_uu):
    """
    Hex, supercomputer at Unseen University, powered by an Anthill Inside.

    Owned by UU (owner) and administered by Ponder Stibbons (no corresponding role).
    """
    # TODO: AuthClient needs to move to profile as parent
    auth_client = AuthClient(
        title="Hex",
        organization=org_uu,
        confidential=True,
        website='https://example.org/',
        redirect_uris=['https://example.org/callback'],
    )
    db_session.add(auth_client)
    return auth_client


@pytest.fixture()
def client_hex_credential(db_session, client_hex):
    cred, secret = AuthClientCredential.new(client_hex)
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
):
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
def new_user(db_session):
    user = User(**TEST_DATA['users']['testuser'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_user2(db_session):
    user = User(**TEST_DATA['users']['testuser2'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_user_owner(db_session):
    user = User(**TEST_DATA['users']['test-org-owner'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_user_admin(db_session):
    user = User(**TEST_DATA['users']['test-org-admin'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def new_organization(db_session, new_user_owner, new_user_admin):
    org = Organization(owner=new_user_owner, title="Test org", name='test-org')
    db_session.add(org)

    admin_membership = OrganizationMembership(
        organization=org, user=new_user_admin, is_owner=False, granted_by=new_user_owner
    )
    db_session.add(admin_membership)
    db_session.commit()
    return org


@pytest.fixture()
def new_team(db_session, new_user, new_organization):
    team = Team(title="Owners", organization=new_organization)
    db_session.add(team)
    team.users.append(new_user)
    db_session.commit()
    return team


@pytest.fixture()
def new_project(db_session, new_organization, new_user):
    project = Project(
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
def new_project2(db_session, new_organization, new_user_owner):
    project = Project(
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
def new_main_label(db_session, new_project):
    main_label_a = Label(
        title="Parent Label A", project=new_project, description="A test parent label"
    )
    new_project.all_labels.append(main_label_a)
    label_a1 = Label(title="Label A1", icon_emoji="👍", project=new_project)
    label_a2 = Label(title="Label A2", project=new_project)

    main_label_a.options.append(label_a1)
    main_label_a.options.append(label_a2)
    main_label_a.required = True
    main_label_a.restricted = True
    db_session.commit()

    return main_label_a


@pytest.fixture()
def new_main_label_unrestricted(db_session, new_project):
    main_label_b = Label(
        title="Parent Label B", project=new_project, description="A test parent label"
    )
    new_project.all_labels.append(main_label_b)
    label_b1 = Label(title="Label B1", icon_emoji="👍", project=new_project)
    label_b2 = Label(title="Label B2", project=new_project)

    main_label_b.options.append(label_b1)
    main_label_b.options.append(label_b2)
    main_label_b.required = False
    main_label_b.restricted = False
    db_session.commit()

    return main_label_b


@pytest.fixture()
def new_label(db_session, new_project):
    label_b = Label(title="Label B", icon_emoji="🔟", project=new_project)
    new_project.all_labels.append(label_b)
    db_session.add(label_b)
    db_session.commit()
    return label_b


@pytest.fixture()
def new_proposal(db_session, new_user, new_project):
    proposal = Proposal(
        user=new_user,
        project=new_project,
        title="Test Proposal",
        body="Test proposal description",
    )
    db_session.add(proposal)
    db_session.commit()
    return proposal
