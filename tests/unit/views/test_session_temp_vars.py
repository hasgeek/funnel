from datetime import timedelta
import time

import pytest

from coaster.utils import utcnow
from funnel.views.helpers import SessionTimeouts, session_timeouts

test_timeout_seconds = 1


def test_session_timeouts_dict():
    st = SessionTimeouts()
    assert isinstance(st.keys_at, set)
    assert st == {}
    assert st.keys_at == set()

    with pytest.raises(ValueError):
        st['test'] = 'not a timestamp'

    st['test'] = timedelta(seconds=1)

    assert st == {'test': timedelta(seconds=1)}
    assert st.keys_at == {'test_at'}

    with pytest.raises(KeyError):
        # Key can't be a dupe
        st['test'] = timedelta(seconds=2)

    # Key can be removed and added again in the unlikely situation where this is needed
    del st['test']
    assert st == {}
    assert st.keys_at == set()

    st['test'] = timedelta(seconds=2)
    assert st == {'test': timedelta(seconds=2)}
    assert st.keys_at == {'test_at'}


@pytest.fixture
def timeout_var():
    session_timeouts['test_timeout'] = timedelta(seconds=test_timeout_seconds)
    yield
    session_timeouts.pop('test_timeout')


def test_session_temp_vars(client, timeout_var):
    with client.session_transaction() as session:
        assert 'test_timeout' not in session
        assert 'test_timeout_at' not in session
        assert 'test_notimeout' not in session
        assert 'test_notimeout_at' not in session

        session['test_timeout'] = 'test1'
        session['test_notimeout'] = 'test2'

    # Hit a lightweight endpoint to trigger the temp var timeout scanner
    client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)

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
    client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)

    # The temp var should be removed now, while the other var remains
    with client.session_transaction() as session:
        assert 'test_timeout' not in session
        assert 'test_timeout_at' not in session
        assert 'test_notimeout' in session
        assert 'test_notimeout_at' not in session

        assert session['test_notimeout'] == 'test2'
