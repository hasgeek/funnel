"""
Tests for search views.

These tests verify the structure of the views, but don't actually test for whether the
views are returning expected results (at this time). Proper search testing requires a
corpus of searchable data in fixtures.
"""

# pylint: disable=redefined-outer-name

from types import SimpleNamespace
from typing import cast

import pytest
from flask import Flask, url_for

from funnel import models
from funnel.views.search import (
    SearchInAccountProvider,
    SearchInProjectProvider,
    get_tsquery,
    search_counts,
    search_providers,
)

from ...conftest import TestClient, scoped_session

search_all_types = list(search_providers.keys())
search_profile_types = [
    k for k, v in search_providers.items() if isinstance(v, SearchInAccountProvider)
]
search_project_types = [
    k for k, v in search_providers.items() if isinstance(v, SearchInProjectProvider)
]


@pytest.fixture
def db_session(db_session_truncate: scoped_session) -> scoped_session:
    """
    Use the database session truncate fixture.

    The default rollback fixture is not compatible with Flask-Executor, which is used
    in the search methods to parallelize tasks.
    """
    return db_session_truncate


# MARK: Tests for datatypes returned by search providers -------------------------------


@pytest.mark.parametrize('stype', search_all_types)
def test_search_all_count_returns_int(
    stype: str, all_fixtures: SimpleNamespace
) -> None:
    """Assert that all_count() returns an int."""
    assert isinstance(search_providers[stype].all_count(get_tsquery("test")), int)


@pytest.mark.parametrize('stype', search_profile_types)
def test_search_profile_count_returns_int(
    stype: str, org_ankhmorpork: models.Organization, all_fixtures: SimpleNamespace
) -> None:
    """Assert that profile_count() returns an int."""
    assert isinstance(
        cast(SearchInAccountProvider, search_providers[stype]).account_count(
            get_tsquery("test"), org_ankhmorpork
        ),
        int,
    )


@pytest.mark.parametrize('stype', search_project_types)
def test_search_project_count_returns_int(
    stype: str, project_expo2010: models.Project, all_fixtures: SimpleNamespace
) -> None:
    """Assert that project_count() returns an int."""
    assert isinstance(
        cast(SearchInProjectProvider, search_providers[stype]).project_count(
            get_tsquery("test"), project_expo2010
        ),
        int,
    )


@pytest.mark.parametrize('stype', search_all_types)
def test_search_all_returns_query(stype: str, all_fixtures: SimpleNamespace) -> None:
    """Assert that all_query() returns a query."""
    assert isinstance(
        search_providers[stype].all_query(get_tsquery("test")), models.Query
    )


@pytest.mark.parametrize('stype', search_profile_types)
def test_search_profile_returns_query(
    stype: str, org_ankhmorpork: models.Organization, all_fixtures: SimpleNamespace
) -> None:
    """Assert that profile_query() returns a query."""
    assert isinstance(
        cast(SearchInAccountProvider, search_providers[stype]).account_query(
            get_tsquery("test"), org_ankhmorpork
        ),
        models.Query,
    )


@pytest.mark.parametrize('stype', search_project_types)
def test_search_project_returns_query(
    stype: str, project_expo2010: models.Project, all_fixtures: SimpleNamespace
) -> None:
    """Assert that project_query() returns an int."""
    assert isinstance(
        cast(SearchInProjectProvider, search_providers[stype]).project_query(
            get_tsquery("test"), project_expo2010
        ),
        models.Query,
    )


# MARK: Test search functions ----------------------------------------------------------


@pytest.mark.usefixtures('request_context', 'all_fixtures')
def test_search_counts(
    org_ankhmorpork: models.Organization, project_expo2010: models.Project
) -> None:
    """Test that search_counts returns a list of dicts."""
    r1 = search_counts(get_tsquery("test"))
    r2 = search_counts(get_tsquery("test"), account=org_ankhmorpork)
    r3 = search_counts(get_tsquery("test"), project=project_expo2010)

    for resultset in (r1, r2, r3):
        assert isinstance(resultset, list)
        for typeset in resultset:
            assert 'type' in typeset
            assert 'label' in typeset
            assert 'count' in typeset


# MARK: Test views ---------------------------------------------------------------------


@pytest.mark.usefixtures('app_context', 'all_fixtures')
def test_view_search_counts(
    app: Flask,
    client: TestClient,
    org_ankhmorpork: models.Organization,
    project_expo2010: models.Project,
) -> None:
    """Search views return counts as a list of dicts."""
    org_ankhmorpork.make_profile_public()
    r1 = client.get(
        url_for('search'),
        query_string={'q': "test"},
        headers={'Accept': 'application/json'},
    ).get_json()
    r2 = client.get(
        org_ankhmorpork.url_for('search'),
        query_string={'q': "test"},
        headers={'Accept': 'application/json'},
    ).get_json()
    r3 = client.get(
        project_expo2010.url_for('search'),
        query_string={'q': "test"},
        headers={'Accept': 'application/json'},
    ).get_json()

    for resultset in (r1, r2, r3):
        assert isinstance(resultset, dict)
        assert 'counts' in resultset
        for countset in resultset['counts']:
            assert 'type' in countset
            assert 'label' in countset
            assert 'count' in countset


@pytest.mark.usefixtures('app_context', 'all_fixtures')
@pytest.mark.parametrize('stype', search_all_types)
def test_view_search_results_all(client: TestClient, stype: str) -> None:
    """Global search view returns results for each type."""
    resultset = client.get(
        url_for('search'),
        query_string={'q': "test", 'type': stype},
        headers={'Accept': 'application/json'},
    ).get_json()
    assert isinstance(resultset, dict)
    assert 'counts' in resultset
    for countset in resultset['counts']:
        assert 'type' in countset
        assert 'label' in countset
        assert 'count' in countset
    assert 'results' in resultset


@pytest.mark.usefixtures('app_context', 'all_fixtures')
@pytest.mark.parametrize('stype', search_profile_types)
def test_view_search_results_profile(
    client: TestClient, org_ankhmorpork: models.Organization, stype: str
) -> None:
    """Account search view returns results for each type."""
    org_ankhmorpork.make_profile_public()
    resultset = client.get(
        org_ankhmorpork.url_for('search'),
        query_string={'q': "test", 'type': stype},
        headers={'Accept': 'application/json'},
    ).get_json()
    assert isinstance(resultset, dict)
    assert 'counts' in resultset
    for countset in resultset['counts']:
        assert 'type' in countset
        assert 'label' in countset
        assert 'count' in countset
    assert 'results' in resultset


@pytest.mark.usefixtures('app_context', 'all_fixtures')
@pytest.mark.parametrize('stype', search_project_types)
def test_view_search_results_project(
    client: TestClient, project_expo2010: models.Project, stype: str
) -> None:
    """Project search view returns results for each type."""
    resultset = client.get(
        project_expo2010.url_for('search'),
        query_string={'q': "test", 'type': stype},
        headers={'Accept': 'application/json'},
    ).get_json()
    assert isinstance(resultset, dict)
    assert 'counts' in resultset
    for countset in resultset['counts']:
        assert 'type' in countset
        assert 'label' in countset
        assert 'count' in countset
    assert 'results' in resultset
