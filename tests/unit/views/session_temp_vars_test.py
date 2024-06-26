"""Test handling of temporary variables in cookie session."""

# pylint: disable=redefined-outer-name

import time
from collections.abc import Generator
from datetime import timedelta

import pytest

from coaster.utils import utcnow

from funnel.views.helpers import SessionTimeouts, session_timeouts

from ...conftest import TestClient

test_timeout_seconds = 1


def test_session_timeouts_dict() -> None:
    st = SessionTimeouts()
    assert isinstance(st.keys_at, set)
    assert st == {}  # pylint: disable=use-implicit-booleaness-not-comparison
    assert st.keys_at == set()

    with pytest.raises(ValueError, match='must be a timedelta'):
        st['test'] = 'not a timestamp'  # type: ignore[assignment]

    st['test'] = timedelta(seconds=1)

    assert st == {'test': timedelta(seconds=1)}
    assert st.keys_at == {'test_at'}

    with pytest.raises(KeyError):
        # Key can't be a dupe
        st['test'] = timedelta(seconds=2)

    # Key can be removed and added again in the unlikely situation where this is needed
    del st['test']
    assert st == {}  # pylint: disable=use-implicit-booleaness-not-comparison
    assert st.keys_at == set()

    st['test'] = timedelta(seconds=2)
    assert st == {'test': timedelta(seconds=2)}
    assert st.keys_at == {'test_at'}


def test_session_intersection() -> None:
    st = SessionTimeouts()
    st['test'] = timedelta(seconds=1)
    fake_session_intersection = {'test': 'value', 'other': 'other_value'}
    fake_session_disjoint = {'other': 'other_value', 'yet_other': 'yet_other_value'}

    assert st.has_overlap_with(fake_session_intersection)
    assert not st.has_overlap_with(fake_session_disjoint)


@pytest.fixture
def _timeout_var() -> Generator[None, None, None]:
    session_timeouts['test_timeout'] = timedelta(seconds=test_timeout_seconds)
    yield
    session_timeouts.pop('test_timeout')


@pytest.mark.flaky(reruns=1)  # Rerun in case assert with timedelta fails
@pytest.mark.usefixtures('_timeout_var')
def test_session_temp_vars(client: TestClient) -> None:
    with client.session_transaction() as session:
        assert 'test_timeout' not in session
        assert 'test_timeout_at' not in session
        assert 'test_notimeout' not in session
        assert 'test_notimeout_at' not in session

        session['test_timeout'] = 'test1'
        session['test_notimeout'] = 'test2'

    # Hit a lightweight endpoint to trigger the temp var timeout scanner
    _ = client.get('/api/baseframe/1/csrf/refresh').text

    with client.session_transaction() as session:
        assert 'test_timeout' in session
        assert 'test_timeout_at' in session
        assert 'test_notimeout' in session
        assert 'test_notimeout_at' not in session

        assert session['test_timeout'] == 'test1'
        assert session['test_timeout_at'] > utcnow() - timedelta(seconds=1)
        assert session['test_notimeout'] == 'test2'

    # Sleep for the timeout period
    time.sleep(test_timeout_seconds)

    # Hit a lightweight endpoint to trigger the temp var timeout scanner again
    _ = client.get('/api/baseframe/1/csrf/refresh').text

    # The temp var should be removed now, while the other var remains
    with client.session_transaction() as session:
        assert 'test_timeout' not in session
        assert 'test_timeout_at' not in session
        assert 'test_notimeout' in session
        assert 'test_notimeout_at' not in session

        assert session['test_notimeout'] == 'test2'
